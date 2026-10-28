from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException
from sqlalchemy import select

from app.core.db.session import sessions
from app.features.account.models import Account, Assignment
from app.features.briefs.models import Brief
from app.features.briefs.schemas import BriefView
from app.features.clinician.schemas import PatientDetail, PatientPage, PatientSummary
from app.features.meals.models import Meal
from app.features.meals.schemas import MealView
from app.features.medications.models import MedicationEvent
from app.features.medications.schemas import EventView
from app.features.patients.models import Patient

PATIENT_LIMIT = 50
RECORD_LIMIT = 100


def assigned_patients(user_id: str):
    # Recheck authoritative role AND assignment in every record query. Never use
    # browser role claims or an earlier account response as an access grant.
    return select(Patient.id).join(Assignment, Assignment.patient_id == Patient.id).join(
        Account, Account.clerk_user_id == Assignment.clinician_id).where(
            Account.clerk_user_id == user_id, Account.role == "clinician").correlate(None)


def patient_page(user_id: str, offset: int) -> PatientPage:
    with sessions()() as db:
        rows = db.scalars(select(Patient).where(Patient.id.in_(assigned_patients(user_id)))
                          .order_by(Patient.name, Patient.id).offset(offset).limit(PATIENT_LIMIT + 1)).all()
        return PatientPage(patients=[PatientSummary.model_validate(row) for row in rows[:PATIENT_LIMIT]],
                           offset=offset, has_more=len(rows) > PATIENT_LIMIT)


def patient_detail(user_id: str, patient_id: str, start: date | None, end: date | None) -> PatientDetail:
    with sessions()() as db:
        scope = assigned_patients(user_id).where(Patient.id == patient_id)
        patient = db.scalar(select(Patient).where(Patient.id.in_(scope)))
        if patient is None:
            # Unknown and unassigned IDs have identical responses.
            raise HTTPException(404, "Assigned patient unavailable")
        try:
            zone = ZoneInfo(patient.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            raise HTTPException(409, "The patient timezone needs developer configuration") from None
        end = end or datetime.now(timezone.utc).astimezone(zone).date()
        if not date(1900, 1, 1) <= end <= date(2100, 12, 31):
            raise HTTPException(422, "Choose dates between 1900-01-01 and 2100-12-31")
        start = start or max(date(1900, 1, 1), end - timedelta(days=29))
        if not date(1900, 1, 1) <= start <= date(2100, 12, 31):
            raise HTTPException(422, "Choose dates between 1900-01-01 and 2100-12-31")
        if start > end or (end - start).days >= 90:
            raise HTTPException(422, "Choose an inclusive date range of 1 to 90 days")
        # Local calendar midnights, including DST changes; medication timestamps
        # use a half-open UTC interval. Meals/briefs retain their saved local day.
        lower = datetime.combine(start, time.min, zone).astimezone(timezone.utc)
        upper = datetime.combine(end + timedelta(days=1), time.min, zone).astimezone(timezone.utc)
        meals = db.scalars(select(Meal).where(
            Meal.patient_id.in_(scope), Meal.local_day >= start, Meal.local_day <= end)
            .order_by(Meal.local_day.desc(), Meal.created_at.desc(), Meal.id).limit(RECORD_LIMIT + 1)).all()
        events = db.scalars(select(MedicationEvent).where(
            MedicationEvent.patient_id.in_(scope), MedicationEvent.occurred_at >= lower,
            MedicationEvent.occurred_at < upper).order_by(
                MedicationEvent.occurred_at.desc(), MedicationEvent.id).limit(RECORD_LIMIT + 1)).all()

        def latest_brief(kind: str):
            row = db.scalar(select(Brief).where(
                Brief.patient_id.in_(scope), Brief.kind == kind,
                Brief.local_day >= start, Brief.local_day <= end)
                .order_by(Brief.created_at.desc(), Brief.id).limit(1))
            return BriefView.model_validate(row) if row else None

        return PatientDetail(
            patient=PatientSummary.model_validate(patient), start_date=start, end_date=end,
            record_limit=RECORD_LIMIT,
            meals=[MealView.model_validate(row) for row in meals[:RECORD_LIMIT]],
            meals_truncated=len(meals) > RECORD_LIMIT,
            medication_events=[EventView.model_validate(row) for row in events[:RECORD_LIMIT]],
            medication_events_truncated=len(events) > RECORD_LIMIT,
            morning_brief=latest_brief("morning"), evening_brief=latest_brief("evening"))
