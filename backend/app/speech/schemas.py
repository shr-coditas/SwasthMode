from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Transcript(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class SpeechSource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    feature: Literal["meals", "medications", "health_logs", "briefs"]
    # For briefs this is the brief ID; otherwise the completed request ID.
    source_id: UUID
