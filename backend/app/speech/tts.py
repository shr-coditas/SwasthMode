import asyncio
import logging

from cartesia import AsyncCartesia
from fastapi import HTTPException

from app.ai.guardrails import check_output
from app.ai.nemo import SafetyUnavailable, allowed
from app.core.config import settings
from app.core.provider_errors import describe

log = logging.getLogger("swasthmode.speech")


async def synthesize(text: str) -> bytes:
    cfg = settings()
    if not text or len(text) > 10000 or not check_output(text):
        raise HTTPException(422, "This response is unavailable for speech. The text remains available")
    if any(not value or value.startswith("replace_") for value in
           (cfg.cartesia_api_key.get_secret_value(), cfg.cartesia_model, cfg.cartesia_voice_id)):
        raise HTTPException(503, "Configure the Cartesia key, model and voice ID. The text remains available")
    try:
        if not await allowed(text, "output"):
            raise HTTPException(422, "Speech was blocked by the output checks. The text remains available")
    except SafetyUnavailable:
        raise HTTPException(503, "Speech safety checking is unavailable. The text remains available") from None
    try:
        async with asyncio.timeout(cfg.speech_timeout_seconds):
            async with AsyncCartesia(api_key=cfg.cartesia_api_key.get_secret_value(),
                                     timeout=cfg.speech_timeout_seconds, max_retries=0) as client:
                async with client.tts.with_streaming_response.generate(
                    model_id=cfg.cartesia_model, voice=cfg.cartesia_voice_id, transcript=text,
                    language="en", save=False,
                    output_format={"container": "wav", "encoding": "pcm_s16le", "sample_rate": 24000},
                ) as response:
                    audio = bytearray()
                    async for chunk in response.iter_bytes():
                        audio.extend(chunk)
                        if len(audio) > 20 * 1024 * 1024:
                            raise ValueError("Audio exceeds the in-memory limit")
        if not audio or audio[:4] != b"RIFF" or audio[8:12] != b"WAVE":
            raise ValueError("No WAV audio returned")
        return bytes(audio)
    except Exception as error:
        log.warning("layer=tts model=%s status=failed error=%s", cfg.cartesia_model, describe(error))
        raise HTTPException(502, "Speech generation failed or timed out. Your saved result and text remain available") from None
