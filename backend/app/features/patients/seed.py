from datetime import UTC, datetime, time, timedelta
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo
from app.core.db.base import now
from app.core.db.session import sessions
from app.features.patients.models import Goal, Measurement, Patient, Prescription
from app.features.meals.models import Meal
from app.features.medications.models import MedicationEvent
from app.features.medications.schemas import MedicationExtraction, PrescriptionView, ReportedField


def seed_medication_events(db, patient: Patient, prescription_id: str):
    prescription = db.get(Prescription, prescription_id)
    if not prescription or prescription.patient_id != patient.id:
        return
    today = now().astimezone(ZoneInfo(patient.timezone)).date()
    for offset in (1, 2):
        event_id = synthetic_id(patient.id + f"/medication-event/{offset}")
        if db.get(MedicationEvent, event_id):
            continue
        local = datetime.combine(today - timedelta(days=offset), time(9), ZoneInfo(patient.timezone))
        clock = local.strftime("%Y-%m-%d %H:%M")
        text = f"I took {prescription.name} {prescription.strength} at {clock}"
        reported = MedicationExtraction(intent="record", taken_evidence=text,
                                        name=ReportedField(value=prescription.name, evidence=prescription.name),
                                        strength=ReportedField(value=prescription.strength, evidence=prescription.strength),
                                        quantity=None, frequency=None,
                                        time_text=ReportedField(value=clock, evidence=clock))
        db.add(MedicationEvent(id=event_id, patient_id=patient.id, prescription_id=prescription.id,
                               source_request_id=synthetic_id(event_id + "/seed-request"),
                               reported=reported.model_dump(mode="json"),
                               prescription_snapshot=PrescriptionView.model_validate(prescription).model_dump(mode="json"),
                               occurred_at=local.astimezone(UTC), timezone=patient.timezone,
                               time_evidence=clock, revision=1, synthetic=True))


def synthetic_id(label: str) -> str:
    return str(uuid5(NAMESPACE_URL, "swasthmode/synthetic/" + label))


def seed():
    profiles = [
        ("asha", "Asha Demo", "Building a regular meal logging routine.", 5000, 7, "Metformin", "500 mg", "twice daily"),
        ("kabir", "Kabir Demo", "Some days have activity data but no sleep measurement.", 6000, 8, "Atorvastatin", "10 mg", "once daily"),
        ("leena", "Leena Demo", "Uses smaller daily goals and has incomplete activity data.", 3500, 7, "Amlodipine", "5 mg", "once daily"),
    ]
    with sessions()() as db, db.begin():
        for slug, name, summary, steps, sleep, medicine, strength, frequency in profiles:
            patient_id = synthetic_id(slug)
            existing = db.get(Patient, patient_id)
            if existing:
                seed_medication_events(db, existing, synthetic_id(slug + "/rx"))
                continue
            db.add(Patient(id=patient_id, name=name, timezone="Asia/Kolkata", summary=summary))
            db.flush()
            db.add(Prescription(id=synthetic_id(slug + "/rx"), patient_id=patient_id,
                                name=medicine, strength=strength, frequency=frequency))
            db.flush()
            seed_medication_events(db, db.get(Patient, patient_id), synthetic_id(slug + "/rx"))
            db.add_all([Goal(patient_id=patient_id, metric="steps", target=steps),
                        Goal(patient_id=patient_id, metric="sleep_hours", target=sleep)])
            today = now().astimezone(ZoneInfo("Asia/Kolkata")).date()
            for offset in range(5):
                values = {"steps": steps - 1000 + offset * 350, "sleep_hours": sleep - .5 + offset * .1}
                if slug == "kabir" and offset % 2 == 0:
                    values.pop("sleep_hours")
                if slug == "leena" and offset == 1:
                    values.pop("steps")
                db.add(Measurement(patient_id=patient_id, day=today - timedelta(days=offset), values=values))
            db.add(Meal(patient_id=patient_id, source_request_id=synthetic_id(slug + "/seed-meal"),
                        local_day=today - timedelta(days=1), meal_type="lunch",
                        foods=[{"name": "rice", "quantity": None, "evidence": "rice and dal"},
                               {"name": "dal", "quantity": None, "evidence": "rice and dal"}],
                        revision=1, insight_status="not_requested", insight=None))
    return "Synthetic profiles and medication events seeded. Existing records were preserved; no AI was called."
