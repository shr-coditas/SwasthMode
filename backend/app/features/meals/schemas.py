from datetime import date, datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MealMessage(StrictModel):
    request_id: UUID
    text: str = Field(min_length=1, max_length=2000)
    conversation_id: UUID | None = None


class Food(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    quantity: str | None = Field(max_length=80)
    evidence: str = Field(min_length=1, max_length=300)


class MealExtraction(StrictModel):
    intent: Literal["create", "update", "greeting", "out_of_scope", "clarify"]
    target_meal_id: str | None
    meal_type: Literal["breakfast", "lunch", "dinner", "snack"] | None
    local_day: date | None
    foods: list[Food] = Field(max_length=30)
    question: str | None = Field(max_length=300)


class MealView(StrictModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    id: str
    local_day: date
    meal_type: str
    foods: list[Food]
    revision: int
    created_at: datetime
    updated_at: datetime
    insight_status: str
    insight: str | None


class MealReply(StrictModel):
    request_id: str
    conversation_id: str
    status: Literal["saved", "clarification", "reply"]
    reply: str
    meal: MealView | None = None
    replayed: bool = False


class InsightOutput(StrictModel):
    observed_foods: list[str] = Field(min_length=1, max_length=30)
    observation: str = Field(min_length=1, max_length=500)
