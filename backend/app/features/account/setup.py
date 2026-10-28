from app.core.db.session import sessions
from app.features.account.models import Account, Assignment
from app.features.patients.models import Patient


def map_account(user_id: str, role: str, patient_id: str | None):
    if not user_id.startswith("user_") or len(user_id) > 100:
        raise ValueError("Supply a Clerk user ID copied from your development dashboard")
    with sessions()() as db, db.begin():
        if patient_id and not db.get(Patient, patient_id):
            raise ValueError("Synthetic patient not found")
        existing = db.get(Account, user_id)
        if existing:
            if existing.role != role or existing.patient_id != patient_id:
                raise ValueError("Account already has a different mapping; edit it deliberately in DBeaver")
            return
        db.add(Account(clerk_user_id=user_id, role=role, patient_id=patient_id))


def assign(clinician_id: str, patient_id: str):
    with sessions()() as db, db.begin():
        clinician = db.get(Account, clinician_id)
        if not clinician or clinician.role != "clinician":
            raise ValueError("Map the clinician account first")
        if not db.get(Patient, patient_id):
            raise ValueError("Synthetic patient not found")
        if not db.get(Assignment, (clinician_id, patient_id)):
            db.add(Assignment(clinician_id=clinician_id, patient_id=patient_id))
