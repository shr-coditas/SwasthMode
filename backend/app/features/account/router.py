from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from app.core.auth.clerk import identity
from app.core.db.session import sessions
from app.features.account.models import Account, Assignment
from app.features.patients.models import Patient

router = APIRouter(prefix="/api/account", tags=["account"])


@router.get("")
def account(user_id: str = Depends(identity)):
    with sessions()() as db:
        row = db.get(Account, user_id)
        if not row:
            return {"setup_required": True, "role": None, "patient": None}
        patient = db.get(Patient, row.patient_id) if row.patient_id else None
        return {"setup_required": False, "role": row.role,
                "patient": {"id": patient.id, "name": patient.name, "timezone": patient.timezone,
                            "summary": patient.summary} if patient else None,
                "assigned_patient_count": db.scalar(select(func.count()).select_from(Assignment).join(
                    Account, Account.clerk_user_id == Assignment.clinician_id).where(
                    Account.clerk_user_id == user_id, Account.role == "clinician")) if row.role == "clinician" else 0}
