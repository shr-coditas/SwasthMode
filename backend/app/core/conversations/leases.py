from dataclasses import dataclass
from datetime import timedelta
import time

from fastapi import HTTPException
from sqlalchemy import or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.conversations.models import Conversation
from app.core.db.base import new_id, now
from app.core.db.session import sessions
from app.core.requests.models import ClientRequest


@dataclass
class Turn:
    patient_id: str
    conversation_id: str
    request_id: str
    owner: str
    version: int
    state: dict
    checkpoint: dict
    feature: str = "meals"
    expired: bool = False
    parent: "Turn | None" = None
    deadline: float | None = None


def acquire(patient_id: str, request_id: str, fingerprint: str, conversation_id: str | None,
            feature: str = "meals", parent: Turn | None = None) -> Turn | dict:
    cfg = settings()
    timestamp = now()
    with sessions()() as db, db.begin():
        if parent:
            owned(db, parent)
        previous = db.get(ClientRequest, (patient_id, request_id))
        if previous:
            if previous.fingerprint != fingerprint or previous.feature != feature:
                raise HTTPException(409, "This request ID was already used for different input")
            if previous.status == "completed":
                return {**previous.result, "replayed": True}
        db.execute(insert(Conversation).values(
            id=new_id(), patient_id=patient_id, feature=feature, state={}, version=0,
            expires_at=timestamp + timedelta(hours=cfg.conversation_hours), updated_at=timestamp,
        ).on_conflict_do_nothing(index_elements=["patient_id", "feature"]))
        row = db.scalar(select(Conversation).where(
            Conversation.patient_id == patient_id, Conversation.feature == feature))
        if conversation_id and row.id != conversation_id:
            raise HTTPException(409, "This conversation ended. Start a new report; old confirmations cannot be reused")
        if row.expires_at <= timestamp and conversation_id and feature in ("meals", "health_meals"):
            raise HTTPException(409, "This meal conversation expired. Start a new message; saved meals remain")
        expired = row.expires_at <= timestamp
        if feature == "health_logs" and not expired and row.state.get("inflight_request_id") not in (None, request_id):
            raise HTTPException(409, "An interrupted unified request needs its exact retry before a new message. Reload to see committed progress")
        if previous and previous.checkpoint and (
            previous.checkpoint["base_version"] != row.version or expired
        ):
            if expired and feature == "medications":
                raise HTTPException(409, "This medication confirmation or report expired. No event was saved from this retry. Send a new complete report")
            raise HTTPException(409, "This request belongs to an older conversation state. Start a new message")
        owner = new_id()
        claimed = db.execute(update(Conversation).where(
            Conversation.id == row.id, Conversation.version == row.version,
            or_(Conversation.lease_owner.is_(None), Conversation.lease_expires_at <= timestamp),
        ).values(lease_owner=owner, lease_expires_at=timestamp + timedelta(seconds=cfg.turn_lease_seconds)))
        if claimed.rowcount != 1:
            raise HTTPException(409, "Your previous message is still processing. Please retry shortly")
        if not previous:
            previous = ClientRequest(patient_id=patient_id, request_id=request_id,
                                     feature=feature, fingerprint=fingerprint)
            db.add(previous)
        checkpoint = previous.checkpoint or {"base_version": row.version, "extraction": None,
                                            "reported_at": parent.checkpoint["reported_at"] if parent else timestamp.isoformat()}
        previous.checkpoint = checkpoint
        previous.status = "pending"
        if feature == "health_logs":
            row.state = {**row.state, "inflight_request_id": request_id}
        return Turn(patient_id, row.id, request_id, owner, row.version,
                    {} if expired and feature in ("meals", "health_meals") else dict(row.state), dict(checkpoint), feature, expired, parent)


def owned(db: Session, turn: Turn):
    if turn.deadline is not None and time.monotonic() >= turn.deadline:
        raise HTTPException(409, "The unified turn deadline ended. Retry the same request to recover progress")
    if turn.parent:
        owned(db, turn.parent)
    # This conditional update takes a row lock only for this short transaction.
    count = db.execute(update(Conversation).where(
        Conversation.id == turn.conversation_id, Conversation.patient_id == turn.patient_id,
        Conversation.feature == turn.feature,
        Conversation.lease_owner == turn.owner, Conversation.lease_expires_at > now(),
        Conversation.version == turn.version,
        (Conversation.expires_at > now()) if turn.feature == "health_logs" and not turn.expired else True,
    ).values(updated_at=now()))
    if count.rowcount != 1:
        raise HTTPException(409, "The conversation lease ended. Reload before retrying")


def release(turn: Turn):
    with sessions()() as db, db.begin():
        if turn.feature == "health_logs":
            row = db.scalar(select(Conversation).where(Conversation.id == turn.conversation_id,
                Conversation.lease_owner == turn.owner).with_for_update())
            request = db.get(ClientRequest, (turn.patient_id, turn.request_id))
            if row and not (request.checkpoint or {}).get("operation"):
                row.state = {k: v for k, v in row.state.items() if k != "inflight_request_id"}
        db.execute(update(Conversation).where(
            Conversation.id == turn.conversation_id, Conversation.lease_owner == turn.owner,
        ).values(lease_owner=None, lease_expires_at=None))
