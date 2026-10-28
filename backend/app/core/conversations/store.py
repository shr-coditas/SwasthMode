from datetime import timedelta
from sqlalchemy import update
from app.core.config import settings
from app.core.conversations.leases import Turn, owned
from app.core.conversations.models import Conversation
from app.core.db.base import now
from app.core.db.session import sessions
from app.core.requests.models import ClientRequest


def checkpoint(turn: Turn, extraction: dict, key: str = "extraction"):
    with sessions()() as db, db.begin():
        owned(db, turn)
        request = db.get(ClientRequest, (turn.patient_id, turn.request_id))
        request.checkpoint = {**request.checkpoint, key: extraction}


def complete(db, turn: Turn, state: dict, result: dict):
    # Caller already checked ownership in this same transaction.
    request = db.get(ClientRequest, (turn.patient_id, turn.request_id))
    request.result = result
    request.status = "completed"
    db.execute(update(Conversation).where(
        Conversation.id == turn.conversation_id, Conversation.lease_owner == turn.owner,
        Conversation.version == turn.version,
    ).values(state=state, version=turn.version + 1, lease_owner=None, lease_expires_at=None,
             expires_at=now() + timedelta(hours=settings().conversation_hours), updated_at=now()))
