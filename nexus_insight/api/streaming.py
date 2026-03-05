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
    Includes a heartbeat to keep the connection alive.
    """
    heartbeat = heartbeat_generator(interval=10)
    
    # We need to pull from both generators. 
    # Since event_generator is the primary, we wrap it.
    
    event_task = asyncio.create_task(anext(event_generator, None))
    heartbeat_task = asyncio.create_task(anext(heartbeat))
    
    try:
        while True:
            done, pending = await asyncio.wait(
                [event_task, heartbeat_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            if event_task in done:
                event = event_task.result()
                if event is None: # Generator exhausted
                    break
                
                yield {
                    "event": event.event,
                    "data": json.dumps(event.data, default=str)
                }
                event_task = asyncio.create_task(anext(event_generator, None))
                
            if heartbeat_task in done:
                hb = heartbeat_task.result()
                yield hb
                heartbeat_task = asyncio.create_task(anext(heartbeat))
                
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
    finally:
        event_task.cancel()
        heartbeat_task.cancel()

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
