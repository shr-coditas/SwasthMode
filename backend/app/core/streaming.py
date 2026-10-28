import asyncio
import json
from fastapi.responses import StreamingResponse


def stream_reply(result: dict) -> StreamingResponse:
    async def events():
        # Structured extraction finishes before this stream. Never stream an uncommitted success.
        for word in result["reply"].split(" "):
            yield f"event: text\ndata: {json.dumps({'text': word + ' '})}\n\n"
            await asyncio.sleep(0)
        yield f"event: result\ndata: {json.dumps(result)}\n\n"
    return StreamingResponse(events(), media_type="text/event-stream", headers={
        "Cache-Control": "no-store", "X-Accel-Buffering": "no",
    })
