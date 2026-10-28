from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field
from app.features.meals.schemas import StrictModel
from app.features.medications.schemas import MedicationMessage, PendingView


class PlannedStep(StrictModel):
    feature: Literal["meals", "medications"]
    text: str = Field(min_length=1, max_length=2000)
    start: int = Field(ge=0, le=1999)
    end: int = Field(ge=1, le=2000)


class Plan(StrictModel):
    disposition: Literal["logging", "greeting", "unsupported", "clarify"]
    steps: list[PlannedStep] = Field(max_length=4)


class HealthMessage(StrictModel):
    request_id: UUID
    conversation_id: UUID | None = None
    text: str = Field(default="", max_length=2000)
    action: Literal["report", "answer", "confirm", "cancel", "continue", "abandon"] = "report"
    workflow_id: UUID | None = None
    step_id: UUID | None = None
    question_id: UUID | None = None
    question_version: int | None = Field(default=None, ge=0)
    medication: MedicationMessage | None = None


class StepView(StrictModel):
    id: str
    feature: Literal["meals", "medications"]
    status: Literal["queued", "clarification", "confirmation", "saved", "cancelled", "stopped"]
    reply: str = ""
    record_id: str | None = None


class Pending(StrictModel):
    id: str
    step_id: str
    feature: Literal["meals", "medications"]
    question_version: int
    expires_at: datetime
    medication: PendingView | None = None
    specialist_conversation_id: str | None = None


class HealthReply(StrictModel):
    request_id: str
    conversation_id: str
    workflow_id: str | None = None
    version: int
    status: Literal["pending", "ready", "completed", "reply", "expired"]
    reply: str
    steps: list[StepView] = Field(default_factory=list)
    pending: Pending | None = None
    replayed: bool = False
