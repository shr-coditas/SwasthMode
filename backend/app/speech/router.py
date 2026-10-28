import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from starlette.concurrency import run_in_threadpool

from app.core.auth.permissions import PatientAccess, patient_access
from app.core.db.session import sessions
from app.core.requests.models import ClientRequest
from app.features.briefs.models import Brief
from app.features.medications.service import present
from app.speech.schemas import SpeechSource, Transcript
from app.speech.stt import transcribe
from app.speech.tts import synthesize

router = APIRouter(prefix="/api/speech", tags=["speech"])
MAX_UPLOAD = 2 * 1024 * 1024


@router.post("/transcriptions", response_model=Transcript)
async def transcription(request: Request, access: PatientAccess = Depends(patient_access)):
    mime = request.headers.get("content-type", "").lower().replace(" ", "")
    if mime not in ("audio/webm", "audio/webm;codecs=opus"):
        raise HTTPException(415, "Record WebM/Opus in desktop Chrome")
    # Stream the raw body with a hard byte ceiling, without a multipart spool/file.
    audio = bytearray()
    try:
        async with asyncio.timeout(20):
            async for chunk in request.stream():
                if len(audio) + len(chunk) > MAX_UPLOAD:
                    raise HTTPException(413, "Recording exceeds 2 MiB. Record a shorter message")
                audio.extend(chunk)
    except TimeoutError:
        raise HTTPException(408, "Audio upload timed out. Record again or type your message") from None
    if len(audio) < 4 or audio[:4] != b"\x1a\x45\xdf\xa3":
        raise HTTPException(422, "No usable WebM recording was received")
    return Transcript(text=await transcribe(bytes(audio), mime))


def source_text(patient_id: str, source: SpeechSource) -> str:
    # Resolve only server-owned, committed text in a short-lived DB session.
    with sessions()() as db:
        if source.feature == "briefs":
            brief = db.get(Brief, str(source.source_id))
            if not brief or brief.patient_id != patient_id:
                raise HTTPException(404, "Saved speech source is unavailable")
            return f"{brief.text}\nA small focus. {brief.focus_text}"
        row = db.get(ClientRequest, (patient_id, str(source.source_id)))
        if not row or row.feature != source.feature or row.status != "completed" or not row.result:
            raise HTTPException(404, "Completed speech source is unavailable")
        if source.feature == "medications":
            return present(row.result).reply
        return row.result.get("reply", "")


@router.post("/audio")
async def audio(source: SpeechSource, access: PatientAccess = Depends(patient_access)):
    text = await run_in_threadpool(source_text, access.patient_id, source)
    return Response(await synthesize(text), media_type="audio/wav", headers={"Cache-Control": "no-store"})
