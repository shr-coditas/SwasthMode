from datetime import date

from pydantic import BaseModel, ConfigDict

from app.features.briefs.schemas import BriefView
from app.features.meals.schemas import MealView
from app.features.medications.schemas import EventView


class PatientSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    timezone: str
    summary: str


class PatientPage(BaseModel):
    patients: list[PatientSummary]
    offset: int
    has_more: bool


class PatientDetail(BaseModel):
    patient: PatientSummary
    start_date: date
    end_date: date
    record_limit: int
    meals: list[MealView]
    meals_truncated: bool
    medication_events: list[EventView]
    medication_events_truncated: bool
    morning_brief: BriefView | None
    evening_brief: BriefView | None
