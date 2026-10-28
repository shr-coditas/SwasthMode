import logging
import time
from typing import TypeVar

from openai import AsyncAzureOpenAI, AsyncOpenAI
from pydantic import BaseModel
from app.core.config import settings

T = TypeVar("T", bound=BaseModel)
log = logging.getLogger("swasthmode.ai")


class ProviderFailure(Exception):
    pass


async def structured(prompt: str, context: str, schema: type[T]) -> T:
    cfg = settings()
    if not cfg.ai_api_key.get_secret_value() or not cfg.ai_model:
        raise ProviderFailure("Configure the text AI key and model/deployment")
    if cfg.ai_provider == "azure" and not cfg.ai_api_version:
        raise ProviderFailure("Configure the Azure API version")
    common = dict(api_key=cfg.ai_api_key.get_secret_value(),
                  timeout=cfg.provider_timeout_seconds, max_retries=cfg.provider_retries)
    client = (AsyncAzureOpenAI(azure_endpoint=cfg.ai_base_url, api_version=cfg.ai_api_version, **common)
              if cfg.ai_provider == "azure" else AsyncOpenAI(base_url=cfg.ai_base_url, **common))
    started = time.monotonic()
    try:
        async with client:
            result = await client.chat.completions.parse(
                model=cfg.ai_model, response_format=schema,
                messages=[{"role": "system", "content": prompt}, {"role": "user", "content": context}],
            )
        parsed = result.choices[0].message.parsed
        if parsed is None:
            raise ProviderFailure("The provider declined or returned no structured result")
        return parsed
    except ProviderFailure:
        raise
    except Exception:
        raise ProviderFailure("Text AI failed or returned an invalid response. Nothing new was saved") from None
    finally:
        log.info("model=%s duration_ms=%d", cfg.ai_model, (time.monotonic() - started) * 1000)
