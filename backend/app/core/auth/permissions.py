from dataclasses import dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import Depends, HTTPException
from app.core.auth.clerk import identity
from app.core.db.session import sessions
from app.features.account.models import Account
from app.features.patients.models import Patient


@dataclass(frozen=True)
class PatientAccess:
    clerk_user_id: str
    patient_id: str
    name: str
    timezone: str


def clinician_access(user_id: str = Depends(identity)) -> str:
    with sessions()() as db:
        account = db.get(Account, user_id)
        if not account or account.role != "clinician":
            raise HTTPException(403, "A configured clinician account is required")
    return user_id


def patient_access(user_id: str = Depends(identity)) -> PatientAccess:
    with sessions()() as db:
        account = db.get(Account, user_id)
        if not account:
            raise HTTPException(403, "Account setup required")
        if account.role != "patient":
            raise HTTPException(403, "A patient account is required")
        patient = db.get(Patient, account.patient_id)
        if not patient:
            raise HTTPException(403, "Patient association is unavailable")
        try:
            ZoneInfo(patient.timezone)
        except ZoneInfoNotFoundError:
            raise HTTPException(409, "The patient timezone needs developer configuration") from None
        return PatientAccess(user_id, patient.id, patient.name, patient.timezone)
