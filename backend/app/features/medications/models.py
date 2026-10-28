from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base, new_id, now


class MedicationEvent(Base):
    __tablename__ = "medication_events"
    __table_args__ = (
        UniqueConstraint("patient_id", "source_request_id"),
        CheckConstraint("revision > 0", name="revision_positive"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    prescription_id: Mapped[str] = mapped_column(ForeignKey("prescriptions.id"))
    source_request_id: Mapped[str] = mapped_column(String(36))
    reported: Mapped[dict] = mapped_column(JSONB)
    prescription_snapshot: Mapped[dict] = mapped_column(JSONB)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    timezone: Mapped[str] = mapped_column(String(60))
    time_evidence: Mapped[str] = mapped_column(String(100))
    revision: Mapped[int] = mapped_column(Integer, default=1)
    synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MedicationQuestion(Base):
    __tablename__ = "medication_questions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"))
    step_id: Mapped[str] = mapped_column(String(36), unique=True)
    question_version: Mapped[int] = mapped_column(Integer)
    medication_id: Mapped[str] = mapped_column(ForeignKey("prescriptions.id"))
    proposal: Mapped[dict] = mapped_column(JSONB)
    readback: Mapped[str] = mapped_column(String(2000))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
