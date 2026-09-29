"""Resilient Event Bus & Broadcaster.

Publishes multi-agent execution events to Redis pub/sub (`venture:{id}:events`)
when Redis is available, with automatic fallback to an in-memory `asyncio.Queue`
for local development and testing.
"""

import os
import json
import asyncio
from datetime import datetime, timezone
from typing import Dict, Set, Optional, AsyncGenerator, Any

# Global in-memory subscribers per venture_id
_subscribers: Dict[str, Set[asyncio.Queue]] = {}
_redis_client = None


def get_redis_client():
    """Lazily creates an async Redis client if REDIS_URL is configured."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        import redis.asyncio as aioredis
        _redis_client = aioredis.from_url(redis_url, decode_responses=True)
    except Exception:
        _redis_client = False
    return _redis_client


def format_sse_payload(
    event_type: str,
    venture_id: str,
    stage: str,
    progress_pct: int,
    message: str,
    data: Optional[dict] = None
) -> str:
    """Formats an SSE payload envelope."""
    payload = {
        "event_type": event_type,
        "venture_id": venture_id,
        "stage": stage,
        "progress_pct": progress_pct,
        "message": message,
        "data": data or {},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    return f"data: {json.dumps(payload)}\n\n"


async def publish_event(
    venture_id: str,
    stage: Any = "INITIALIZED",
    event_type: str = "STAGE_PROGRESS",
    progress_pct: int = 0,
    message: str = "",
    data: Optional[dict] = None,
    payload: Optional[dict] = None
):
    """Broadcasts an execution event to both in-memory queues and Redis pub/sub."""
    if payload is not None:
        if isinstance(payload, dict):
            if "current_stage" in payload and stage == "INITIALIZED":
                stage = payload["current_stage"]
            if "message" in payload and not message:
                message = payload["message"]
            if data is None:
                data = payload

    stage_str = stage.value if hasattr(stage, "value") else str(stage)

    sse_data = format_sse_payload(
        event_type=event_type,
        venture_id=venture_id,
        stage=stage_str,
        progress_pct=progress_pct,
        message=message,
        data=data
    )

    # 1. In-memory distribution
    if venture_id in _subscribers:
        for queue in list(_subscribers[venture_id]):
            try:
                queue.put_nowait(sse_data)
            except Exception:
                pass

    # 2. Redis pub/sub distribution
    client = get_redis_client()
    if client:
        try:
            channel = f"venture:{venture_id}:events"
            await client.publish(channel, sse_data)
        except Exception:
            pass


async def subscribe_events(venture_id: str) -> AsyncGenerator[str, None]:
    """Subscribes to events for a specific venture, yielding SSE formatted strings."""
    queue: asyncio.Queue = asyncio.Queue()
    if venture_id not in _subscribers:
        _subscribers[venture_id] = set()
    _subscribers[venture_id].add(queue)

    client = get_redis_client()
    redis_pubsub = None
    if client:
        try:
            redis_pubsub = client.pubsub()
            channel = f"venture:{venture_id}:events"
            await redis_pubsub.subscribe(channel)
        except Exception:
            redis_pubsub = None

    try:
        while True:
            # Yield events from the in-memory queue
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=1.0)
                yield msg
                # Check for terminal stages
                if '"stage": "COMPLETED"' in msg or '"stage": "FAILED"' in msg:
                    break
            except asyncio.TimeoutError:
                # Keep-alive ping comment to prevent SSE timeout
                yield ": keep-alive\n\n"
    finally:
        if venture_id in _subscribers and queue in _subscribers[venture_id]:
            _subscribers[venture_id].remove(queue)
            if not _subscribers[venture_id]:
                del _subscribers[venture_id]
        if redis_pubsub:
            try:
                await redis_pubsub.unsubscribe(f"venture:{venture_id}:events")
                await redis_pubsub.close()
            except Exception:
                pass
