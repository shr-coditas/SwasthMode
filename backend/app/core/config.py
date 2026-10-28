from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parents[3] / ".env",
                                      extra="ignore", hide_input_in_errors=True)
    database_url: SecretStr
    redis_url: SecretStr = SecretStr("redis://redis:6379/0")
    frontend_origin: str = "http://localhost:5173"
    clerk_secret_key: SecretStr = SecretStr("")
    clerk_issuer: str = ""
    clerk_jwt_key: SecretStr = SecretStr("")
    ai_provider: Literal["openai", "azure"] = "openai"
    ai_api_key: SecretStr = SecretStr("")
    ai_base_url: str = "https://api.openai.com/v1"
    ai_api_version: str = ""
    ai_model: str = ""
    guardrails_mode: Literal["hybrid", "rules_only"] = "hybrid"
    nemo_model: str = ""
    nemo_api_key: SecretStr = SecretStr("")
    nemo_timeout_seconds: float = Field(default=12, ge=3, le=20)
    nemo_max_tokens: int = Field(default=1024, ge=64, le=4096)
    provider_timeout_seconds: float = Field(default=25, ge=5, le=35)
    provider_retries: int = Field(default=1, ge=0, le=1)
    turn_timeout_seconds: int = Field(default=80, ge=65, le=100)
    turn_lease_seconds: int = Field(default=120, ge=110, le=180)
    conversation_hours: int = Field(default=24, ge=1, le=24)
    stt_api_key: SecretStr = SecretStr("")
    stt_base_url: str = ""
    stt_model: str = ""
    cartesia_api_key: SecretStr = SecretStr("")
    cartesia_voice_id: str = ""
    cartesia_model: str = ""
    speech_timeout_seconds: float = Field(default=45, ge=10, le=60)

    @model_validator(mode="after")
    def validate_bounds(self):
        if self.turn_lease_seconds <= self.turn_timeout_seconds + 10:
            raise ValueError("The lease must exceed the turn deadline plus commit time")
        if not self.database_url.get_secret_value().startswith("postgresql+psycopg://"):
            raise ValueError("Use a postgresql+psycopg URL")
        return self


@lru_cache
def settings() -> Settings:
    return Settings()
