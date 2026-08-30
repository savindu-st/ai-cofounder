from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio

router = APIRouter()

@router.get("/ventures/{venture_id}/stream")
async def stream_venture_progress(venture_id: str):
    async def event_generator():
        stages = ["INITIALIZED", "IDEA_ANALYSIS", "MARKET_RESEARCH", "CRITIC_VALIDATION", "BUSINESS_MODEL", "REVENUE_ESTIMATION", "MARKETING", "COMPLETED"]
        for stage in stages:
            yield f"data: {{\"stage\": \"{stage}\", \"status\": \"running\"}}\n\n"
            await asyncio.sleep(0.5)
    return StreamingResponse(event_generator(), media_type="text/event-stream")
