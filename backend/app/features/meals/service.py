import asyncio
import hashlib
import json
import logging
import re
import time
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool
from sqlalchemy.exc import SQLAlchemyError

from app.ai.client import ProviderFailure
from app.ai.guardrails import check_input, check_output
from app.ai.nemo import SafetyUnavailable, allowed
from app.core.auth.permissions import PatientAccess
from app.core.config import settings
from app.core.conversations.leases import acquire, owned, release
from app.core.conversations.store import checkpoint, complete
from app.core.db.base import now
from app.core.db.session import sessions
from app.features.meals.extraction import extract
from app.features.meals.replies import saved_reply
from app.features.meals.schemas import MealExtraction, MealMessage, MealReply, MealView
from app.features.meals.validation import validate_meal
from app.features.meals.repository import MealRepository

log = logging.getLogger("swasthmode.meals")
repository = MealRepository()


async def process(access: PatientAccess, message: MealMessage, *, coordinator=None) -> MealReply:
    started = time.monotonic()
    request_id = str(message.request_id)
    fingerprint = hashlib.sha256(message.model_dump_json().encode()).hexdigest()
    turn = await run_in_threadpool(acquire, access.patient_id, request_id, fingerprint,
                                  str(message.conversation_id) if message.conversation_id else None,
                                  "health_meals" if coordinator else "meals", coordinator)
    if isinstance(turn, dict):
        return MealReply.model_validate(turn)
    if coordinator and message.conversation_id is None:
        # A new unified step must not inherit an unfinished earlier step's draft.
        # The saved meal pointer remains available for explicit corrections.
        turn.state = {k: v for k, v in turn.state.items() if k not in ("messages", "draft")}
    try:
        today = now().astimezone(ZoneInfo(access.timezone)).date()
        meals = await run_in_threadpool(repository.meals, access.patient_id, today)
        messages = (turn.state.get("messages", []) + [message.text.strip()])[-8:]
        context = {"local_day": str(today), "timezone": access.timezone,
                   "messages": messages, "draft": turn.state.get("draft"),
                   "last_saved_meal_id": turn.state.get("last_saved_meal_id"),
                   "today_meals": [m.model_dump(mode="json") for m in meals[:30]]}
        blocked = check_input(message.text)
        greeting = re.fullmatch(r"\s*(hi|hello|hey|good morning|good evening)[!. ]*", message.text, re.I)
        direct_reply = blocked or ("Hello! Tell me what you had to eat, and which meal it was." if greeting else None)
        if direct_reply:
            extraction = None
            question = None
        else:
            safety_input = json.dumps({"feature": "meals", "messages": messages[-5:]}, ensure_ascii=False)
            if not await allowed(safety_input, "input"):
                raise HTTPException(422, "The safety check blocked this message. Please rephrase your meal report")
            if turn.checkpoint.get("extraction"):
                extraction = MealExtraction.model_validate(turn.checkpoint["extraction"])
            else:
                try:
                    remaining = settings().turn_timeout_seconds - (time.monotonic() - started) - 15
                    if remaining <= 0:
                        raise TimeoutError
                    async with asyncio.timeout(remaining):
                        extraction = await extract(context)
                except TimeoutError:
                    raise HTTPException(504, "AI extraction timed out. Retry the same request") from None
                await run_in_threadpool(checkpoint, turn, extraction.model_dump(mode="json"))
            source = "\n".join(messages)
            for item in (turn.state.get("draft") or {}).get("foods", []):
                source += "\n" + item["evidence"]
            for meal in meals:
                source += "\n" + "\n".join(food.evidence for food in meal.foods)
            question = validate_meal(extraction, source, today, meals)
            if not check_output(extraction.question or ""):
                raise HTTPException(422, "Our output rules blocked the extracted question. No meal was saved")
            if not await allowed(extraction.model_dump_json(), "output"):
                raise HTTPException(422, "Safety checking blocked the extracted result. No new meal was saved")
            if extraction.intent == "greeting":
                direct_reply = "Hello! Tell me what you had to eat, and which meal it was."
            elif extraction.intent == "out_of_scope":
                direct_reply = "This view records meals. Use the Medication events view for medication reports. Briefs are planned for a later slice."
        if time.monotonic() - started >= settings().turn_timeout_seconds:
            raise HTTPException(504, "This turn reached its time limit. Retry the same request")

        def save():
            with sessions()() as db, db.begin():
                owned(db, turn)
                state = {**turn.state, "messages": messages}
                result = MealReply(request_id=request_id, conversation_id=turn.conversation_id,
                                   status="reply", reply=direct_reply or question or "")
                if question:
                    state["draft"] = extraction.model_dump(mode="json")
                    result.status = "clarification"
                elif not direct_reply:
                    extraction.local_day = today
                    target = next((m for m in meals if m.id == extraction.target_meal_id), None)
                    meal = repository.write_meal(db, access.patient_id, request_id, extraction,
                                                 target.revision if target else None)
                    result.meal = MealView.model_validate(meal)
                    result.reply = saved_reply(result.meal, extraction.intent == "update")
                    result.status = "saved"
                    state["draft"] = None
                    state["last_saved_meal_id"] = meal.id
                state["last_reply"] = result.reply
                complete(db, turn, state, result.model_dump(mode="json"))
                return result

        result = await run_in_threadpool(save)
        if result.meal:
            from app.tasks.meal_insights import enqueue
            await run_in_threadpool(enqueue, result.meal.id, result.meal.revision)
        return result
    except SafetyUnavailable as error:
        raise HTTPException(503, str(error)) from None
    except ProviderFailure as error:
        raise HTTPException(502, str(error)) from None
    finally:
        # Owner-qualified release cannot clear a newer turn's lease.
        try:
            await run_in_threadpool(release, turn)
        except SQLAlchemyError:
            log.warning("request_id=%s status=lease_release_failed", request_id)
        log.info("request_id=%s duration_ms=%d", request_id, (time.monotonic() - started) * 1000)
