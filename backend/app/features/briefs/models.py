from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base, new_id, now


class Brief(Base):
    __tablename__ = "briefs"
    __table_args__ = (
        UniqueConstraint("patient_id", "source_request_id"),
        CheckConstraint("kind IN ('morning', 'evening')", name="kind_allowed"),
        Index("ix_briefs_patient_kind_day", "patient_id", "kind", "local_day"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"))
    source_request_id: Mapped[str] = mapped_column(String(36))
    kind: Mapped[str] = mapped_column(String(10))
    local_day: Mapped[date] = mapped_column(Date)
    timezone: Mapped[str] = mapped_column(String(60))
    context: Mapped[dict] = mapped_column(JSONB)
    narrative: Mapped[dict] = mapped_column(JSONB)
    text: Mapped[str] = mapped_column(String(6000))
    focus_text: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
