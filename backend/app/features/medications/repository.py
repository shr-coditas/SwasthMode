from fastapi import HTTPException
from sqlalchemy import select, update

from app.core.db.base import now
from app.core.db.session import sessions
from app.features.medications.models import MedicationEvent
from app.features.medications.schemas import EventView, PrescriptionView, Proposal
from app.features.patients.models import Prescription


class MedicationRepository:
    def prescriptions(self, patient_id: str) -> list[PrescriptionView]:
        with sessions()() as db:
            rows = db.scalars(select(Prescription).where(Prescription.patient_id == patient_id).order_by(Prescription.name).limit(100))
            return [PrescriptionView.model_validate(row) for row in rows]

    def events(self, patient_id: str) -> list[EventView]:
        with sessions()() as db:
            rows = db.scalars(select(MedicationEvent).where(MedicationEvent.patient_id == patient_id)
                              .order_by(MedicationEvent.occurred_at.desc()).limit(100))
            return [EventView.model_validate(row) for row in rows]

    def event(self, patient_id: str, event_id: str) -> EventView:
        with sessions()() as db:
            row = db.scalar(select(MedicationEvent).where(MedicationEvent.id == event_id,
                                                         MedicationEvent.patient_id == patient_id))
            if row is None:
                raise HTTPException(404, "Recorded event unavailable")
            return EventView.model_validate(row)

    def write(self, db, patient_id: str, request_id: str, proposal: Proposal) -> EventView:
        prescription = db.scalar(select(Prescription).where(Prescription.id == proposal.medication_id,
                                                           Prescription.patient_id == patient_id).with_for_update())
        if not prescription or PrescriptionView.model_validate(prescription) != proposal.prescription:
            raise HTTPException(409, "The prescription reference changed. Send a new report for a new readback")
        if proposal.operation == "correct_time":
            changed = db.execute(update(MedicationEvent).where(
                MedicationEvent.id == proposal.event_id, MedicationEvent.patient_id == patient_id,
                MedicationEvent.prescription_id == proposal.medication_id,
                MedicationEvent.revision == proposal.event_revision,
            ).values(occurred_at=proposal.occurred_at, timezone=proposal.timezone,
                     time_evidence=proposal.time_evidence, revision=MedicationEvent.revision + 1, updated_at=now()))
            if changed.rowcount != 1:
                raise HTTPException(409, "This event changed. Reload and request a new time correction")
            row = db.get(MedicationEvent, proposal.event_id)
        else:
            row = MedicationEvent(patient_id=patient_id, prescription_id=proposal.medication_id,
                                  source_request_id=request_id, reported=proposal.reported.model_dump(mode="json"),
                                  prescription_snapshot=proposal.prescription.model_dump(mode="json"),
                                  occurred_at=proposal.occurred_at, timezone=proposal.timezone,
                                  time_evidence=proposal.time_evidence)
            db.add(row)
        db.flush()
        return EventView.model_validate(row)
