import asyncio
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta
import hashlib
import logging
import re
import time
from uuid import UUID, uuid5
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from app.ai.client import ProviderFailure
from app.ai.guardrails import check_input
from app.ai.nemo import SafetyUnavailable
from app.core.config import settings
from app.core.conversations.leases import acquire, owned, release
from app.core.conversations.models import Conversation
from app.core.conversations.store import complete
from app.core.db.base import new_id, now
from app.core.db.session import sessions
from app.core.requests.models import ClientRequest
from app.features.health_logs.planner import plan, validate
from app.features.health_logs.schemas import HealthMessage, HealthReply, Plan
from app.features.meals.schemas import MealMessage, MealReply
from app.features.meals.service import process as meal_process
from app.features.medications.schemas import MedicationMessage, MedicationReply
from app.features.medications.service import process as medication_process

log = logging.getLogger("swasthmode.health_logs")
EXPIRED = "This unified conversation or question expired. Nothing was saved from this reply. Saved steps remain; start a new report."


def progress(turn, operation):
    # Child replay identity is persisted BEFORE calling the specialist. Parent ownership
    # also fences each child checkpoint/write, even after a process loses its lease.
    with sessions()() as db, db.begin():
        owned(db, turn)
        request = db.get(ClientRequest, (turn.patient_id, turn.request_id))
        request.checkpoint = {**request.checkpoint, "operation": operation}
        row = db.get(Conversation, turn.conversation_id)
        row.state = {**row.state, "workflow": operation.get("workflow")}


def conversation(patient_id):
    with sessions()() as db:
        row = db.scalar(select(Conversation).where(Conversation.patient_id == patient_id,
                                                  Conversation.feature == "health_logs"))
        if not row:
            return {"id": None, "expired": False, "last_result": None, "retry": None}
        workflow = row.state.get("workflow") or {}
        expired = row.expires_at <= now() or bool(workflow.get("expires_at") and
            datetime.fromisoformat(workflow["expires_at"]) <= now()) or bool(workflow.get("pending") and
            datetime.fromisoformat(workflow["pending"]["expires_at"]) <= now())
        request = db.get(ClientRequest, (patient_id, row.state.get("inflight_request_id", "")))
        operation = (request.checkpoint or {}).get("operation", {}) if request else {}
        return {"id": row.id, "version": row.version, "expired": expired, "last_result": row.state.get("last_result"),
                "workflow": workflow or None, "retry": operation.get("message") if row.expires_at > now() else None,
                "interrupted": bool(row.state.get("inflight_request_id")) and row.expires_at > now()}


def bind(message, turn, workflow):
    pending = workflow.get("pending")
    if datetime.fromisoformat(workflow["expires_at"]) <= now():
        raise HTTPException(409, "This workflow's local day ended. Saved records remain; start a new report")
    if (not message.conversation_id or str(message.conversation_id) != turn.conversation_id
            or str(message.workflow_id) != workflow.get("id")):
        raise HTTPException(409, "This reply does not belong to the current unified workflow. Reload its current question")
    if pending:
        if (str(message.step_id) != pending["step_id"] or str(message.question_id) != pending["id"]
                or message.question_version != pending["question_version"]
                or pending["question_version"] != turn.version):
            raise HTTPException(409, "This is not the current question. No consent was transferred; reload")
        if datetime.fromisoformat(pending["expires_at"]) <= now():
            raise HTTPException(409, EXPIRED)
    elif message.question_version != turn.version:
        raise HTTPException(409, "This workflow changed. Reload before continuing")
    elif message.action == "continue" and str(message.step_id) != next(
            (s["id"] for s in workflow["steps"] if s["status"] == "queued"), None):
        raise HTTPException(409, "That is not the next queued step. Reload before continuing")
    return pending


def result(turn, workflow, reply=None, expired=False):
    pending = workflow.get("pending") if workflow and not expired else None
    steps = workflow.get("steps", []) if workflow else []
    ready = any(s["status"] == "queued" for s in steps)
    return HealthReply(request_id=turn.request_id, conversation_id=turn.conversation_id,
        workflow_id=workflow.get("id") if workflow else None, version=turn.version + 1,
        status="expired" if expired else "pending" if pending else "ready" if ready else "completed" if steps else "reply",
        reply=reply or ("Continue to the next report. Earlier saved steps remain saved." if ready else "This workflow is complete. Saved records are listed below."),
        steps=[{k: s[k] for k in ("id", "feature", "status", "reply", "record_id")} for s in steps],
        pending=pending)


async def process(access, message: HealthMessage):
    fingerprint = hashlib.sha256(message.model_dump_json().encode()).hexdigest()
    turn = await run_in_threadpool(acquire, access.patient_id, str(message.request_id), fingerprint,
        str(message.conversation_id) if message.conversation_id else None, "health_logs")
    if isinstance(turn, dict):
        return HealthReply.model_validate(turn)
    turn.deadline = time.monotonic() + settings().turn_timeout_seconds
    try:
        async with asyncio.timeout(settings().turn_timeout_seconds):
            operation = deepcopy(turn.checkpoint.get("operation") or {})
            workflow = deepcopy(operation.get("workflow", turn.state.get("workflow")))
            direct = None
            if not operation:
                if turn.expired and message.action != "report":
                    direct = EXPIRED
                elif message.action == "report":
                    question_expired = bool(workflow and workflow.get("pending") and
                        datetime.fromisoformat(workflow["pending"]["expires_at"]) <= now())
                    day_expired = bool(workflow and datetime.fromisoformat(workflow["expires_at"]) <= now())
                    if workflow and (workflow.get("pending") or any(s["status"] == "queued" for s in workflow["steps"])) and not turn.expired and not question_expired and not day_expired:
                        raise HTTPException(409, "Finish or abandon the current workflow before a new report")
                    if not message.text.strip() or message.medication:
                        raise HTTPException(422, "Send the meal/medication report as text")
                    workflow = None
                    direct = check_input(message.text, feature="health_logs")
                    if re.fullmatch(r"\s*(yes|no|confirm|ok|okay)\s*[.!]?", message.text, re.I):
                        direct = EXPIRED if turn.expired else "Use the current question controls. A generic reply cannot confirm medication."
                    if not direct:
                        routing = Plan.model_validate(turn.checkpoint["plan"]) if turn.checkpoint.get("plan") else await plan(message.text)
                        validate(routing, message.text)
                        # plan() safety-checks before this checkpoint; retries use only that checked plan.
                        from app.core.conversations.store import checkpoint
                        await run_in_threadpool(checkpoint, turn, routing.model_dump(mode="json"), "plan")
                        if routing.disposition != "logging":
                            direct = {"greeting": "Hello! Tell me about meals or medication you already took.",
                                "unsupported": "This view records meals and medication already taken. Use Daily briefs for briefs; other domains and medical advice are unsupported.",
                                "clarify": "Send up to four clearly separated meal/medication reports, preserving each complete medication statement."}[routing.disposition]
                        else:
                            local = datetime.fromisoformat(turn.checkpoint["reported_at"]).astimezone(ZoneInfo(access.timezone))
                            midnight = datetime.combine(local.date() + timedelta(days=1), datetime.min.time(), tzinfo=ZoneInfo(access.timezone))
                            workflow = {"id": new_id(), "reported_at": turn.checkpoint["reported_at"],
                                "expires_at": midnight.isoformat(), "pending": None, "steps": [
                                {"id": new_id(), "feature": s.feature, "text": s.text, "status": "queued",
                                 "reply": "", "record_id": None, "conversation_id": None} for s in routing.steps]}
                else:
                    if not workflow:
                        raise HTTPException(409, "There is no current workflow. Send a new report")
                    pending = bind(message, turn, workflow)
                    if message.action == "abandon":
                        # This stops only unsaved steps. It never rolls back saved records.
                        for step in workflow["steps"]:
                            if step["status"] not in ("saved", "cancelled"):
                                step["status"] = "stopped"
                        workflow["pending"] = None
                        direct = "Stopped the unfinished steps. Previously saved records remain saved."
                    elif message.action == "continue":
                        if pending or message.text or message.medication:
                            raise HTTPException(409, "Answer the current question before continuing")
                    elif not pending:
                        raise HTTPException(409, "There is no current question to answer")
                    elif pending["feature"] == "meals":
                        if message.action != "answer" or not message.text.strip() or message.medication:
                            raise HTTPException(422, "Answer this meal question with text")
                    elif message.action not in ("answer", "confirm", "cancel"):
                        raise HTTPException(422, "Use the current medication question controls")
                operation = {"message": message.model_dump(mode="json"), "workflow": workflow, "direct": direct}
            direct = operation.get("direct")
            if not direct and workflow and "step_reply" not in operation:
                step = next((s for s in workflow["steps"] if s["status"] in ("queued", "clarification", "confirmation")), None)
                if step:
                    child_id = str(uuid5(UUID(turn.request_id), step["id"]))
                    pending = workflow.get("pending")
                    if not operation.get("child"):
                        if step["feature"] == "meals":
                            child = MealMessage(request_id=child_id, conversation_id=step["conversation_id"],
                                text=message.text if pending else step["text"])
                        else:
                            if pending and pending.get("medication"):
                                q = pending["medication"]
                                supplied = message.medication
                                if message.action not in ("confirm", "cancel") or not supplied:
                                    raise HTTPException(422, "Use confirm or cancel for this exact medication readback")
                                expected = MedicationMessage(request_id=child_id,
                                    conversation_id=pending["specialist_conversation_id"], action=message.action,
                                    text="confirm" if message.action == "confirm" else "cancel", question_id=q["id"],
                                    step_id=q["step_id"], medication_id=q["medication_id"], question_version=q["question_version"])
                                if supplied.model_copy(update={"request_id": UUID(child_id)}) != expected:
                                    raise HTTPException(409, "The medication readback binding changed. Reload before confirming")
                                child = expected
                            else:
                                if pending and (message.action != "answer" or message.medication or not message.text.strip()):
                                    raise HTTPException(422, "Send a fresh complete medication report for this step")
                                child = MedicationMessage(request_id=child_id, conversation_id=step["conversation_id"],
                                    text=message.text if pending else step["text"])
                        operation["child"] = child.model_dump(mode="json")
                        await run_in_threadpool(progress, turn, operation)
                    child = operation["child"]
                    question_expiry = min(datetime.fromisoformat(workflow["expires_at"]),
                        datetime.fromisoformat(pending["expires_at"])) if pending else datetime.fromisoformat(workflow["expires_at"])
                    child_deadline = min(turn.deadline, time.monotonic() + (question_expiry - now()).total_seconds())
                    coordinator = replace(turn, checkpoint={**turn.checkpoint,
                        "reported_at": workflow["reported_at"] if step["status"] == "queued" else turn.checkpoint["reported_at"]}, deadline=child_deadline)
                    if question_expiry and question_expiry <= now():
                        def recovered():
                            with sessions()() as db:
                                saved = db.get(ClientRequest, (access.patient_id, child_id))
                                return saved.result if saved and saved.status == "completed" and saved.feature == "health_" + step["feature"] and saved.fingerprint == hashlib.sha256(
                                    (MealMessage.model_validate(child) if step["feature"] == "meals" else MedicationMessage.model_validate(child)).model_dump_json().encode()).hexdigest() else None
                        recovered_result = await run_in_threadpool(recovered)
                        if recovered_result:
                            response = (MealReply if step["feature"] == "meals" else MedicationReply).model_validate(recovered_result)
                        else:
                            # No new specialist work after question expiry. A completed
                            # child result may still be recovered truthfully above.
                            response = (MealReply(request_id=child_id, conversation_id=step["conversation_id"] or turn.conversation_id, status="reply", reply=EXPIRED)
                                if step["feature"] == "meals" else MedicationReply(request_id=child_id,
                                    conversation_id=step["conversation_id"] or turn.conversation_id, status="expired", reply=EXPIRED))
                    else:
                        response = (await meal_process(access, MealMessage.model_validate(child), coordinator=coordinator)
                            if step["feature"] == "meals" else
                            await medication_process(access, MedicationMessage.model_validate(child), coordinator=coordinator))
                    step["conversation_id"] = response.conversation_id
                    step["reply"] = response.reply
                    record = response.meal if step["feature"] == "meals" else response.event
                    step["record_id"] = record.id if record else None
                    workflow["pending"] = None
                    if record:
                        step["status"] = "saved"
                    elif message.action == "cancel":
                        step["status"] = "cancelled"
                    elif response.status in ("clarification", "confirmation"):
                        step["status"] = response.status
                        medication = response.pending if step["feature"] == "medications" else None
                        workflow["pending"] = {"id": new_id(), "step_id": step["id"], "feature": step["feature"],
                            "question_version": turn.version + 1,
                            "expires_at": min(datetime.fromisoformat(workflow["expires_at"]),
                                medication.expires_at if medication else now() + timedelta(minutes=15), now() + timedelta(minutes=15)).isoformat(),
                            "medication": medication.model_dump(mode="json") if medication else None,
                            "specialist_conversation_id": response.conversation_id}
                    else:
                        step["status"] = "stopped"
                    operation["workflow"] = workflow
                    operation["step_reply"] = response.reply
                    # The child result itself is already durably replayable. Even if this
                    # checkpoint fails, its exact persisted body recovers that same result.
                    await run_in_threadpool(progress, turn, operation)
            reply = result(turn, workflow, direct or operation.get("step_reply"), direct == EXPIRED)

            def finish():
                with sessions()() as db, db.begin():
                    owned(db, turn)
                    complete(db, turn, {"workflow": workflow, "last_result": reply.model_dump(mode="json")}, reply.model_dump(mode="json"))
            await run_in_threadpool(finish)
            return reply
    except TimeoutError:
        raise HTTPException(504, "Unified processing paused. Some steps may already be saved. Retry this exact request to recover committed progress") from None
    except (ProviderFailure, SafetyUnavailable) as error:
        raise HTTPException(503, "Unified processing paused; earlier saved steps remain. Retry this exact request. " + str(error)) from None
    except HTTPException as error:
        raise HTTPException(error.status_code, "Earlier saved steps remain saved. " + str(error.detail), headers=error.headers) from None
    finally:
        try:
            await run_in_threadpool(release, turn)
        except SQLAlchemyError:
            log.warning("request_id=%s status=lease_release_failed", turn.request_id)
