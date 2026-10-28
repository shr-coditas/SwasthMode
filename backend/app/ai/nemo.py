"""NeMo validates messages; it never generates application replies or writes records."""
import asyncio
import logging
from pathlib import Path
from typing import Literal

import yaml

from app.core.config import settings

log = logging.getLogger("swasthmode.guardrails")


class SafetyUnavailable(Exception):
    pass


def build_rails():
    # Library diagnostics can include prompts. Suppress that logger subtree.
    library_log = logging.getLogger("nemoguardrails")
    library_log.addHandler(logging.NullHandler())
    library_log.propagate = False
    library_log.setLevel(logging.CRITICAL)
    from nemoguardrails import LLMRails, RailsConfig

    cfg = settings()
    key = cfg.nemo_api_key.get_secret_value() or cfg.ai_api_key.get_secret_value()
    if not key or not cfg.nemo_model or cfg.nemo_model.startswith("replace_"):
        raise SafetyUnavailable("Configure NEMO_MODEL and the safety provider key for hybrid guardrails")
    parameters = {"api_key": key}
    if cfg.ai_provider == "azure":
        if not cfg.ai_api_version:
            raise SafetyUnavailable("Configure the Azure API version for safety checks")
        parameters.update(azure_endpoint=cfg.ai_base_url, azure_deployment=cfg.nemo_model,
                          api_version=cfg.ai_api_version)
    else:
        parameters["base_url"] = cfg.ai_base_url
    config = yaml.safe_load(Path(__file__).with_name("nemo_config.yml").read_text(encoding="utf-8"))
    config["models"] = [{"type": "main", "engine": cfg.ai_provider,
                         "model": cfg.nemo_model, "parameters": parameters}]
    for prompt in config["prompts"]:
        prompt["max_tokens"] = cfg.nemo_max_tokens
    # Per-check instance: do not share mutable conversation caches or clients across
    # patients or the fresh asyncio event loops used by Celery jobs.
    return LLMRails(RailsConfig.from_content(yaml_content=yaml.safe_dump(config)), verbose=False)


async def allowed(text: str, direction: Literal["input", "output"]) -> bool:
    if settings().guardrails_mode == "rules_only":
        log.info("layer=nemo status=explicitly_disabled")
        return True
    try:
        from nemoguardrails.rails.llm.options import RailStatus, RailType
        async with asyncio.timeout(settings().nemo_timeout_seconds):
            rails = await asyncio.to_thread(build_rails)
            result = await rails.check_async(
                messages=[{"role": "user" if direction == "input" else "assistant", "content": text}],
                rail_types=[RailType.INPUT if direction == "input" else RailType.OUTPUT],
            )
        # We do not accept silently rewritten clinical/logging data. Only an exact
        # pass is usable; blocked or modified results require a fresh user message.
        passed = result.status == RailStatus.PASSED and result.content == text
        log.info("layer=nemo direction=%s status=%s", direction, "allowed" if passed else "blocked")
        return passed
    except SafetyUnavailable:
        raise
    except Exception:
        log.warning("layer=nemo direction=%s status=unavailable", direction)
        raise SafetyUnavailable("NeMo safety checking is unavailable. No new domain record was saved") from None
