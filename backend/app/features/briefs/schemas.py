from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

BriefKind = Literal["morning", "evening"]
Focus = Literal["log_meal", "record_activity", "reflect"]
Opening = Literal["overview", "check_in", "reflection"]


class BriefRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    kind: BriefKind


class Fact(BaseModel):
    id: str
    text: str
    sources: list[str]


class BriefContext(BaseModel):
    kind: BriefKind
    local_day: date
    timezone: str
    captured_at: datetime
    window_start: date
    window_end: date
    facts: list[Fact]
    missing: list[str]
    limits: list[str]


class Narrative(BaseModel):
    model_config = ConfigDict(extra="forbid")
    opening: Opening
    fact_ids: list[str] = Field(min_length=1, max_length=6)
    focus: Focus


class BriefView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    kind: BriefKind
    local_day: date
    timezone: str
    created_at: datetime
    context: BriefContext
    narrative: Narrative
    text: str
    focus_text: str


class BriefReply(BaseModel):
    request_id: str
    status: Literal["saved", "reused"]
    reply: str
    brief: BriefView
    reused: bool
    replayed: bool = False
    reuse_until: datetime
