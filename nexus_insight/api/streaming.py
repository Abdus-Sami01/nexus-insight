import asyncio
import json
import logging
from typing import AsyncGenerator, Any, Dict
from sse_starlette.sse import ServerSentEvent
from nexus_insight.api.schemas import SSEEvent

logger = logging.getLogger(__name__)

async def sse_generator(event_generator: AsyncGenerator[SSEEvent, None]) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Wraps an async generator of SSEEvent to yield ServerSentEvent formatting.
    """
    try:
        async for event in event_generator:
            yield {
                "event": event.event,
                "data": json.dumps(event.data, default=str)
            }
            
        # End of stream
        yield {
            "event": "progress",
            "data": json.dumps({"node": "END", "pct": 100})
        }
    except asyncio.CancelledError:
        logger.info("SSE connection cancelled by client")
    except Exception as e:
        logger.error(f"SSE generator error: {e}")
        yield {
            "event": "error",
            "data": json.dumps({"code": "INTERNAL_ERROR", "message": str(e)})
        }

async def heartbeat_generator(interval: int = 15) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Yields heartbeat events to keep the connection alive.
    """
    while True:
        await asyncio.sleep(interval)
        yield {
            "event": "heartbeat",
            "data": json.dumps({"ts": str(asyncio.get_event_loop().time())})
        }
