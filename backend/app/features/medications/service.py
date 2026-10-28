import asyncio
from datetime import datetime, timedelta
import hashlib
import logging
import re
import time

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from app.ai.client import ProviderFailure
from app.ai.guardrails import check_input, check_output
from app.ai.nemo import SafetyUnavailable, allowed
from app.core.auth.permissions import PatientAccess
from app.core.config import settings
from app.core.conversations.leases import acquire, owned, release
from app.core.conversations.models import Conversation
from app.core.conversations.store import checkpoint, complete
from app.core.db.base import new_id, now
from app.core.db.session import sessions
from app.core.requests.models import ClientRequest
from app.features.medications.extraction import extract
from app.features.medications.matching import match
from app.features.medications.models import MedicationQuestion
from app.features.medications.replies import EXPIRED, STALE, readback, saved_reply
from app.features.medications.repository import MedicationRepository
from app.features.medications.schemas import (
    MedicationExtraction, MedicationMessage, MedicationReply, PendingView, Proposal,
)
from app.features.medications.validation import Clarification, local_time, validate_report

repository = MedicationRepository()
log = logging.getLogger("swasthmode.medications")


def pending_view(row: MedicationQuestion) -> PendingView:
    return PendingView(id=row.id, step_id=row.step_id, medication_id=row.medication_id,
                       question_version=row.question_version, expires_at=row.expires_at, readback=row.readback)


def present(result: dict) -> MedicationReply:
    reply = MedicationReply.model_validate(result)
    if reply.event:
        reply.reply = saved_reply(reply.event, result.get("reply") == "time_corrected")
    return reply


def conversation(patient_id: str) -> dict:
    with sessions()() as db:
        row = db.scalar(select(Conversation).where(Conversation.patient_id == patient_id,
                                                  Conversation.feature == "medications"))
        if not row:
            return {"id": None, "expired": False, "last_reply": None, "pending": None}
        question = db.scalar(select(MedicationQuestion).where(
            MedicationQuestion.id == row.state.get("pending_id"), MedicationQuestion.patient_id == patient_id))
        expired = row.expires_at <= now() or bool(question and question.expires_at <= now())
        pending = (pending_view(question).model_dump(mode="json") if question and not expired
                   and question.status == "pending" and question.question_version == row.version else None)
        last = row.state.get("last_result")
        return {"id": row.id, "expired": expired, "pending": pending,
                "last_reply": EXPIRED if expired else present(last).reply if last else None}


async def process(access: PatientAccess, message: MedicationMessage, *, coordinator=None) -> MedicationReply:
    started = time.monotonic()
    request_id = str(message.request_id)
    fingerprint = hashlib.sha256(message.model_dump_json().encode()).hexdigest()
    turn = await run_in_threadpool(acquire, access.patient_id, request_id, fingerprint,
                                  str(message.conversation_id) if message.conversation_id else None,
                                  "health_medications" if coordinator else "medications", coordinator)
    if isinstance(turn, dict):
        return present(turn)
    proposal = None
    direct = None
    extraction = None
    try:
        try:
            async with asyncio.timeout(settings().turn_timeout_seconds):
                direct = check_input(message.text, feature="medications")
                if not direct and message.action in ("confirm", "cancel"):
                    if not re.fullmatch(r"\s*(yes|confirm|cancel|no)\s*[.!]?", message.text, re.I):
                        direct = "Use the confirmation or cancel control for that exact question, or send a new complete report."
                elif not direct and re.fullmatch(r"\s*(yes|no|confirm|ok|okay)\s*[.!]?", message.text, re.I):
                    direct = EXPIRED if turn.expired else "A bare reply cannot record an event. Please send a new complete report and confirm its readback."
                elif not direct and re.fullmatch(r"\s*(hi|hello|hey)[!. ]*", message.text, re.I):
                    direct = "Hello! Report one medication event already taken, with 'now' or a local YYYY-MM-DD HH:MM time."
                elif not direct:
                    if not await allowed(message.model_dump_json(), "input"):
                        raise HTTPException(422, "Safety checking blocked this report. No event was saved")
                    prescriptions = await run_in_threadpool(repository.prescriptions, access.patient_id)
                    reported_at = datetime.fromisoformat(turn.checkpoint["reported_at"])
                    if message.action == "correct_time":
                        if not message.event_id or not message.event_revision:
                            raise Clarification("Select a recorded event to correct its time.")
                        event = await run_in_threadpool(repository.event, access.patient_id, str(message.event_id))
                        if event.revision != message.event_revision:
                            raise Clarification("This event changed. Reload it before requesting a time correction.")
                        instant = local_time(message.text.strip(), access.timezone, reported_at)
                        prescription = next((item for item in prescriptions if item.id == event.prescription_id), None)
                        if not prescription or prescription != event.prescription_snapshot:
                            raise Clarification("The prescription reference is unavailable or changed since this event was recorded. No time correction was made.")
                        proposal = Proposal(operation="correct_time", medication_id=event.prescription_id,
                                            reported=event.reported, prescription=prescription, occurred_at=instant,
                                            timezone=access.timezone, time_evidence=message.text.strip(), uncertain_match=False,
                                            event_id=event.id, event_revision=event.revision)
                    else:
                        extraction = (MedicationExtraction.model_validate(turn.checkpoint["extraction"])
                                      if turn.checkpoint.get("extraction") else await extract(message.text))
                        await run_in_threadpool(checkpoint, turn, extraction.model_dump(mode="json"))
                        instant = validate_report(extraction, message.text, access.timezone, reported_at)
                        prescription, uncertain = match(extraction.name.value, prescriptions)
                        if not prescription:
                            raise Clarification("I could not identify one prescription for your report. Send a new complete report with the exact medicine name from your prescription list.")
                        proposal = Proposal(operation="record", medication_id=prescription.id,
                                            reported=extraction, prescription=prescription, occurred_at=instant,
                                            timezone=access.timezone, time_evidence=extraction.time_text.value,
                                            uncertain_match=uncertain)
                    await run_in_threadpool(checkpoint, turn, proposal.model_dump(mode="json"), "proposal")
                    if not check_output(readback(proposal)) or not await allowed(proposal.model_dump_json(), "output"):
                        raise HTTPException(422, "Safety checking blocked this readback. No event was saved")
        except Clarification as error:
            direct = str(error)
        except TimeoutError:
            raise HTTPException(504, "This turn timed out. Retry the exact same request") from None

        def save():
            with sessions()() as db, db.begin():
                owned(db, turn)
                row = db.get(Conversation, turn.conversation_id)
                timestamp = now()
                if time.monotonic() - started >= settings().turn_timeout_seconds:
                    raise HTTPException(504, "This turn timed out. Retry the exact same request")
                if proposal and not turn.expired and row.expires_at <= timestamp:
                    raise HTTPException(409, EXPIRED)
                current = db.scalar(select(MedicationQuestion).where(
                    MedicationQuestion.id == turn.state.get("pending_id"),
                    MedicationQuestion.patient_id == access.patient_id).with_for_update())
                result = MedicationReply(request_id=request_id, conversation_id=turn.conversation_id,
                                         status="clarification" if direct else "reply", reply=direct or "")
                referenced = (db.scalar(select(MedicationQuestion).where(
                    MedicationQuestion.id == str(message.question_id),
                    MedicationQuestion.patient_id == access.patient_id,
                )) if direct and message.question_id else None)
                if direct and re.fullmatch(r"\s*(yes|no|confirm|ok|okay)\s*[.!]?", message.text, re.I) and (
                    turn.expired or bool(current and current.expires_at <= timestamp)
                    or bool(referenced and (referenced.expires_at <= timestamp or referenced.status == "expired"))
                    or (current is None and turn.state.get("last_result", {}).get("status") == "expired")
                ):
                    result.status, result.reply = "expired", EXPIRED
                if message.action in ("confirm", "cancel") and not direct:
                    question = db.scalar(select(MedicationQuestion).where(
                        MedicationQuestion.id == str(message.question_id),
                        MedicationQuestion.patient_id == access.patient_id).with_for_update())
                    expired = (turn.expired or row.expires_at <= timestamp or
                               bool(question and (question.expires_at <= timestamp or question.status == "expired")))
                    bound = (question is not None and current is not None and question.id == current.id
                             and question.status == "pending" and message.conversation_id is not None
                             and question.conversation_id == str(message.conversation_id) == turn.conversation_id
                             and question.step_id == str(message.step_id)
                             and question.medication_id == str(message.medication_id)
                             and question.question_version == message.question_version == turn.version)
                    if expired:
                        result.status, result.reply = "expired", EXPIRED
                    elif not bound:
                        result.reply = STALE
                    elif message.action == "cancel":
                        question.status = "cancelled"
                        result.reply = "Cancelled that readback. No event was saved. Send a new complete report when ready."
                    else:
                        accepted = Proposal.model_validate(question.proposal)
                        if not re.fullmatch(r"\s*(yes|confirm)\s*[.!]?", message.text, re.I):
                            raise HTTPException(422, "This action needs explicit confirmation of the readback")
                        request_extraction = accepted.model_dump(mode="json")
                        request = db.get(ClientRequest, (turn.patient_id, turn.request_id))
                        if not request.checkpoint.get("proposal"):
                            raise HTTPException(409, "The confirmation checkpoint is unavailable. Retry the same request")
                        if request.checkpoint["proposal"] != request_extraction:
                            raise HTTPException(409, "The confirmation changed. Send a new report")
                        result.event = repository.write(db, access.patient_id, request_id, accepted)
                        result.status = "saved"
                        result.reply = "time_corrected" if accepted.operation == "correct_time" else "event_recorded"
                        question.status = "confirmed"
                if current and current.status == "pending":
                    current.status = "expired" if turn.expired or current.expires_at <= timestamp else "superseded"
                state = {"pending_id": None}
                if proposal and not direct:
                    question = MedicationQuestion(patient_id=access.patient_id, conversation_id=turn.conversation_id,
                                                  step_id=new_id(), question_version=turn.version + 1,
                                                  medication_id=proposal.medication_id,
                                                  proposal=proposal.model_dump(mode="json"), readback=readback(proposal),
                                                  expires_at=timestamp + timedelta(minutes=15))
                    db.add(question)
                    db.flush()
                    result.pending = pending_view(question)
                    result.status, result.reply = "confirmation", question.readback
                    state["pending_id"] = question.id
                state["last_result"] = result.model_dump(mode="json")
                complete(db, turn, state, result.model_dump(mode="json"))
                return result.model_dump(mode="json")

        if message.action == "confirm" and not direct:
            def confirmation_checkpoint():
                with sessions()() as db:
                    question = db.scalar(select(MedicationQuestion).where(
                        MedicationQuestion.id == str(message.question_id), MedicationQuestion.patient_id == access.patient_id))
                    return Proposal.model_validate(question.proposal).model_dump(mode="json") if question else None
            candidate = await run_in_threadpool(confirmation_checkpoint)
            if candidate:
                await run_in_threadpool(checkpoint, turn, candidate, "proposal")
        return present(await run_in_threadpool(save))
    except SafetyUnavailable as error:
        raise HTTPException(503, str(error)) from None
    except ProviderFailure as error:
        raise HTTPException(502, str(error)) from None
    finally:
        try:
            await run_in_threadpool(release, turn)
        except SQLAlchemyError:
            log.warning("request_id=%s status=lease_release_failed", request_id)
