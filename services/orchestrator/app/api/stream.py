"""Server-Sent Events (SSE) Streaming Endpoint.

Emits standardized event envelopes to connected clients for real-time
stage transitions, progress percentages, warnings, and HITL interrupts.
"""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from services.orchestrator.app.orchestration.event_bus import (
    subscribe_events,
    format_sse_payload,
)

router = APIRouter()


def create_sse_event(
    event_type: str,
    venture_id: str,
    stage: str,
    progress_pct: int,
    message: str,
    data: dict = None
) -> str:
    """Formats an SSE message using the standardized architecture event envelope."""
    return format_sse_payload(
        event_type=event_type,
        venture_id=venture_id,
        stage=stage,
        progress_pct=progress_pct,
        message=message,
        data=data
    )


@router.get("/ventures/{venture_id}/stream")
async def stream_venture_progress(venture_id: str):
    """Streams live multi-agent execution events to the frontend client from the event bus."""
    return StreamingResponse(
        subscribe_events(venture_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
