from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db.base import Base


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint("role IN ('patient', 'clinician')", name="role"),
        CheckConstraint("(role = 'patient' AND patient_id IS NOT NULL) OR "
                        "(role = 'clinician' AND patient_id IS NULL)", name="role_patient_mapping"),
    )
    clerk_user_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    role: Mapped[str] = mapped_column(String(20))
    patient_id: Mapped[str | None] = mapped_column(ForeignKey("patients.id"))


class Assignment(Base):
    __tablename__ = "clinician_assignments"
    clinician_id: Mapped[str] = mapped_column(ForeignKey("accounts.clerk_user_id"), primary_key=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), primary_key=True)
