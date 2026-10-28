from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from app.core.auth.permissions import PatientAccess, patient_access
from app.core.db.base import now
from app.core.db.session import sessions
from app.core.conversations.models import Conversation
from app.core.streaming import stream_reply
from app.features.meals.schemas import MealMessage, MealReply, MealView
from app.features.meals.service import process, repository
from sqlalchemy import select

router = APIRouter(prefix="/api/meals", tags=["meals"])


@router.get("", response_model=list[MealView])
def list_meals(access: PatientAccess = Depends(patient_access)):
    return repository.meals(access.patient_id)


@router.get("/conversation")
def conversation(access: PatientAccess = Depends(patient_access)):
    with sessions()() as db:
        row = db.scalar(select(Conversation).where(
            Conversation.patient_id == access.patient_id, Conversation.feature == "meals"))
        if not row:
            return {"id": None, "expired": False, "last_reply": None}
        expired = row.expires_at <= now()
        return {"id": row.id, "expired": expired,
                "last_reply": None if expired else row.state.get("last_reply")}


@router.post("/messages", response_model=MealReply)
async def message(body: MealMessage, stream: bool = Query(False),
                  access: PatientAccess = Depends(patient_access)):
    result = (await process(access, body)).model_dump(mode="json")
    return stream_reply(result) if stream else JSONResponse(result)
