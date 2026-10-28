from fastapi import APIRouter, Depends
from app.core.auth.permissions import PatientAccess, patient_access
from app.features.health_logs.schemas import HealthMessage, HealthReply
from app.features.health_logs.service import conversation, process

router = APIRouter(prefix="/api/health-logs", tags=["unified logging"])


@router.get("/conversation")
def current(access: PatientAccess = Depends(patient_access)):
    return conversation(access.patient_id)


@router.post("/messages", response_model=HealthReply)
async def message(body: HealthMessage, access: PatientAccess = Depends(patient_access)):
    return await process(access, body)
