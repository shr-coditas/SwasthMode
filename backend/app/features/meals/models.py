from datetime import date, datetime
from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db.base import Base, new_id, now


class Meal(Base):
    __tablename__ = "meals"
    __table_args__ = (
        UniqueConstraint("patient_id", "source_request_id"),
        CheckConstraint("revision > 0", name="revision_positive"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    source_request_id: Mapped[str] = mapped_column(String(36))
    local_day: Mapped[date] = mapped_column(Date, index=True)
    meal_type: Mapped[str] = mapped_column(String(20))
    foods: Mapped[list] = mapped_column(JSONB)
    revision: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    insight_status: Mapped[str] = mapped_column(String(20), default="pending")
    insight: Mapped[str | None] = mapped_column(String(1000))
