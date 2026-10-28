from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db.base import Base, now


class ClientRequest(Base):
    __tablename__ = "client_requests"
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    feature: Mapped[str] = mapped_column(String(30))
    fingerprint: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    checkpoint: Mapped[dict | None] = mapped_column(JSONB)
    result: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
