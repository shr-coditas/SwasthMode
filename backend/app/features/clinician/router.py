from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.auth.permissions import clinician_access
from app.features.clinician.queries import patient_detail, patient_page
from app.features.clinician.schemas import PatientDetail, PatientPage

router = APIRouter(prefix="/api/clinician", tags=["clinician"])


@router.get("/patients", response_model=PatientPage)
def patients(offset: int = Query(default=0, ge=0, le=10000), user_id: str = Depends(clinician_access)):
    return patient_page(user_id, offset)


@router.get("/patients/{patient_id}", response_model=PatientDetail)
def detail(patient_id: UUID, start_date: date | None = None, end_date: date | None = None,
           user_id: str = Depends(clinician_access)):
    return patient_detail(user_id, str(patient_id), start_date, end_date)
