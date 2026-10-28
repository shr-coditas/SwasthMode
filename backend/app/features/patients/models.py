from datetime import date
from sqlalchemy import Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db.base import Base, new_id


class Patient(Base):
    __tablename__ = "patients"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(100))
    timezone: Mapped[str] = mapped_column(String(60), default="Asia/Kolkata")
    summary: Mapped[str] = mapped_column(String(500))


class Prescription(Base):
    __tablename__ = "prescriptions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    strength: Mapped[str] = mapped_column(String(60))
    frequency: Mapped[str] = mapped_column(String(100))


class Measurement(Base):
    __tablename__ = "measurements"
    __table_args__ = (UniqueConstraint("patient_id", "day"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    day: Mapped[date] = mapped_column(Date)
    values: Mapped[dict] = mapped_column(JSONB)


class Goal(Base):
    __tablename__ = "goals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    metric: Mapped[str] = mapped_column(String(40))
    target: Mapped[int]
