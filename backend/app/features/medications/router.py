from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.core.auth.permissions import PatientAccess, patient_access
from app.core.streaming import stream_reply
from app.features.medications.schemas import EventView, MedicationMessage, MedicationReply, PrescriptionView
from app.features.medications.service import conversation, process, repository

router = APIRouter(prefix="/api/medications", tags=["medications"])


@router.get("", response_model=list[EventView])
def events(access: PatientAccess = Depends(patient_access)):
    return repository.events(access.patient_id)


@router.get("/prescriptions", response_model=list[PrescriptionView])
def prescriptions(access: PatientAccess = Depends(patient_access)):
    return repository.prescriptions(access.patient_id)


@router.get("/conversation")
def current_conversation(access: PatientAccess = Depends(patient_access)):
    return conversation(access.patient_id)


@router.post("/messages", response_model=MedicationReply)
async def message(body: MedicationMessage, stream: bool = Query(False),
                  access: PatientAccess = Depends(patient_access)):
    result = (await process(access, body)).model_dump(mode="json")
    return stream_reply(result) if stream else JSONResponse(result)
