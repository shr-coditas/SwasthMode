from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db.base import Base, new_id, now


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (UniqueConstraint("patient_id", "feature"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    feature: Mapped[str] = mapped_column(String(30))
    state: Mapped[dict] = mapped_column(JSONB, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    lease_owner: Mapped[str | None] = mapped_column(String(36))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
