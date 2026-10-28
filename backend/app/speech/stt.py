import asyncio
import logging

from fastapi import HTTPException
from openai import AsyncOpenAI

from app.core.config import settings
from app.core.provider_errors import describe

log = logging.getLogger("swasthmode.speech")


async def transcribe(audio: bytes, mime: str) -> str:
    cfg = settings()
    if any(not value or value.startswith("replace_") for value in
           (cfg.stt_api_key.get_secret_value(), cfg.stt_base_url, cfg.stt_model)):
        raise HTTPException(503, "Configure the separate WebM/Opus transcription endpoint, key and model")
    try:
        async with asyncio.timeout(cfg.speech_timeout_seconds):
            async with AsyncOpenAI(api_key=cfg.stt_api_key.get_secret_value(), base_url=cfg.stt_base_url,
                                   timeout=cfg.speech_timeout_seconds, max_retries=0) as client:
                result = await client.audio.transcriptions.create(
                    model=cfg.stt_model, file=("recording.webm", audio, mime), response_format="json")
        text = result.text.strip()
    except Exception as error:
        log.warning("layer=stt model=%s status=failed error=%s", cfg.stt_model, describe(error))
        raise HTTPException(502, "Transcription failed or timed out. Type your message or record again; nothing was logged") from None
    if not text or len(text) > 2000 or any(ord(c) < 32 and c not in "\n\r\t" for c in text):
        raise HTTPException(422, "No usable transcript within 2,000 characters. Try a shorter recording or type your message")
    return text
