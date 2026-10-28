import asyncio
import hashlib
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool

from app.ai.client import ProviderFailure
from app.ai.guardrails import check_input
from app.ai.nemo import SafetyUnavailable, allowed
from app.core.auth.permissions import PatientAccess
from app.core.config import settings
from app.core.conversations.leases import acquire, owned, release
from app.core.conversations.store import checkpoint, complete
from app.core.db.base import now
from app.core.db.session import sessions
from app.core.requests.models import ClientRequest
from app.features.briefs.context import gather
from app.features.briefs.generation import generate
from app.features.briefs.models import Brief
from app.features.briefs.repository import BriefRepository
from app.features.briefs.schemas import BriefContext, BriefReply, BriefRequest, BriefView, Narrative
from app.features.briefs.validation import render, reuse_until

repository = BriefRepository()


def present(result: dict) -> BriefReply:
    status = result["status"]
    return BriefReply.model_validate({**result, "reply":
        "Reused your saved brief with its original context snapshot." if status == "reused" else
        "Your brief was saved with the context snapshot shown below."})


def result_for(row, request_id, reused):
    return {"request_id": request_id, "status": "reused" if reused else "saved", "reused": reused,
            "brief": BriefView.model_validate(row).model_dump(mode="json"),
            "reuse_until": reuse_until(row.kind, row.local_day, row.timezone, row.created_at).isoformat()}


def prepare(turn, access, kind):
    with sessions()() as db, db.begin():
        owned(db, turn)
        timestamp = now()
        today = timestamp.astimezone(ZoneInfo(access.timezone)).date()
        reusable = repository.reusable(db, access.patient_id, kind, today, access.timezone, timestamp)
        if reusable:
            result = result_for(reusable, turn.request_id, True)
            complete(db, turn, {}, result)
            return result, None
        request = db.get(ClientRequest, (turn.patient_id, turn.request_id))
        if request.checkpoint.get("brief_context"):
            context = BriefContext.model_validate(request.checkpoint["brief_context"])
        else:
            context = gather(db, access, kind, timestamp)
            request.checkpoint = {**request.checkpoint, "brief_context": context.model_dump(mode="json")}
        ensure_current(context, access.timezone, timestamp)
        return None, context


def ensure_current(context, timezone, timestamp):
    if (context.timezone != timezone or context.local_day != timestamp.astimezone(ZoneInfo(timezone)).date()
            or timestamp >= reuse_until(context.kind, context.local_day, timezone, context.captured_at)):
        raise HTTPException(409, "This brief context expired. Request a new brief with a new request ID")


def save(turn, access, context, narrative):
    with sessions()() as db, db.begin():
        owned(db, turn)
        timestamp = now()
        ensure_current(context, access.timezone, timestamp)
        row = repository.reusable(db, access.patient_id, context.kind, context.local_day, access.timezone, timestamp)
        reused = row is not None
        if row is None:
            text, focus = render(context, narrative)
            row = Brief(patient_id=access.patient_id, source_request_id=turn.request_id, kind=context.kind,
                        local_day=context.local_day, timezone=context.timezone,
                        context=context.model_dump(mode="json"), narrative=narrative.model_dump(mode="json"),
                        text=text, focus_text=focus, created_at=timestamp)
            db.add(row)
            db.flush()
        result = result_for(row, turn.request_id, reused)
        complete(db, turn, {}, result)
        return result


async def process(access: PatientAccess, body: BriefRequest) -> BriefReply:
    fingerprint = hashlib.sha256(body.model_dump_json().encode()).hexdigest()
    turn = await run_in_threadpool(acquire, access.patient_id, str(body.request_id), fingerprint, None, "briefs")
    if isinstance(turn, dict):
        return present(turn)
    try:
        async with asyncio.timeout(settings().turn_timeout_seconds):
            result, context = await run_in_threadpool(prepare, turn, access, body.kind)
            if result is not None:
                return present(result)
            blocked = check_input(f"Generate a {body.kind} wellness brief.")
            if blocked or not await allowed(context.model_dump_json(), "input"):
                raise HTTPException(422, "Safety checking blocked this brief. No brief was saved")
            if turn.checkpoint.get("brief_narrative"):
                narrative = Narrative.model_validate(turn.checkpoint["brief_narrative"])
            else:
                narrative = await generate(context)
            text, focus = render(context, narrative)
            output = "\n".join([text, focus, *context.missing, *context.limits])
            if not await allowed(output, "output"):
                raise HTTPException(422, "Safety checking blocked the generated brief. No brief was saved")
            await run_in_threadpool(checkpoint, turn, narrative.model_dump(mode="json"), "brief_narrative")
        result = await run_in_threadpool(save, turn, access, context, narrative)
        return present(result)
    except (ProviderFailure, SafetyUnavailable, TimeoutError):
        raise HTTPException(503, "Brief generation or safety checking was unavailable. Retry the same request; no success is being claimed") from None
    finally:
        await run_in_threadpool(release, turn)
