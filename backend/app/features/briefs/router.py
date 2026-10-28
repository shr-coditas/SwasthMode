from fastapi import APIRouter, Depends

from app.core.auth.permissions import PatientAccess, patient_access
from app.features.briefs.schemas import BriefReply, BriefRequest, BriefView
from app.features.briefs.service import process, repository

router = APIRouter(prefix="/api/briefs", tags=["briefs"])


@router.get("", response_model=list[BriefView])
def history(access: PatientAccess = Depends(patient_access)):
    return repository.history(access.patient_id)


@router.post("", response_model=BriefReply)
async def generate(body: BriefRequest, access: PatientAccess = Depends(patient_access)):
    return await process(access, body)
