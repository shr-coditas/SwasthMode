from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MedicationMessage(StrictModel):
    request_id: UUID
    conversation_id: UUID | None = None
    text: str = Field(min_length=1, max_length=2000)
    action: Literal["report", "confirm", "cancel", "correct_time"] = "report"
    question_id: UUID | None = None
    step_id: UUID | None = None
    medication_id: UUID | None = None
    question_version: int | None = Field(default=None, ge=0)
    event_id: UUID | None = None
    event_revision: int | None = Field(default=None, ge=1)


class ReportedField(StrictModel):
    value: str = Field(min_length=1, max_length=100)
    evidence: str = Field(min_length=1, max_length=300)


class MedicationExtraction(StrictModel):
    intent: Literal["record", "clarify", "out_of_scope"]
    taken_evidence: str | None = Field(max_length=300)
    name: ReportedField | None
    strength: ReportedField | None
    quantity: ReportedField | None
    frequency: ReportedField | None
    time_text: ReportedField | None


class PrescriptionView(StrictModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    id: str
    name: str
    strength: str
    frequency: str


class EventView(StrictModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    id: str
    prescription_id: str
    reported: MedicationExtraction
    prescription_snapshot: PrescriptionView
    occurred_at: datetime
    timezone: str
    time_evidence: str
    revision: int
    synthetic: bool
    created_at: datetime
    updated_at: datetime


class Proposal(StrictModel):
    operation: Literal["record", "correct_time"]
    medication_id: str
    reported: MedicationExtraction
    prescription: PrescriptionView
    occurred_at: datetime
    timezone: str
    time_evidence: str
    uncertain_match: bool
    event_id: str | None = None
    event_revision: int | None = None


class PendingView(StrictModel):
    id: str
    step_id: str
    medication_id: str
    question_version: int
    expires_at: datetime
    readback: str


class MedicationReply(StrictModel):
    request_id: str
    conversation_id: str
    status: Literal["saved", "clarification", "confirmation", "reply", "expired"]
    reply: str
    pending: PendingView | None = None
    event: EventView | None = None
    replayed: bool = False
