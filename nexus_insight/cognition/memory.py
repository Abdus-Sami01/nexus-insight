import logging
import json
from typing import List, Dict, Optional
import redis
from nexus_insight.cognition.state import ResearchState, RawSource
from nexus_insight.config import settings

logger = logging.getLogger(__name__)

class MemoryManager:
    """
    Manages short-term (in-state) and long-term (Redis) memory.
    """

    def __init__(self):
        self.redis_client = None
        try:
            self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        except Exception as e:
            logger.warning(f"Redis not available for long-term memory: {e}")

    def save_session(self, state: ResearchState):
        """Persist full research state to Redis"""
        if not self.redis_client:
            return
        
        session_id = state.get("session_id")
        if session_id:
            try:
                # Filter out potentially large content for core state storage if needed
                # But here we store everything for session replay
                self.redis_client.setex(
                    f"session:{session_id}", 
                    86400 * 7,  # 7 days TTL
                    json.dumps(state, default=str)
                )
            except Exception as e:
                logger.error(f"Failed to save session {session_id}: {e}")

    def load_session(self, session_id: str) -> Optional[Dict]:
        """Load research state from Redis"""
        if not self.redis_client:
            return None
        
        try:
            data = self.redis_client.get(f"session:{session_id}")
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None

    def get_source_by_id(self, state: ResearchState, source_id: str) -> Optional[RawSource]:
        """Retrieve a specific source from state"""
        for source in state.get("raw_sources", []):
            if source.id == source_id:
                return source
        return None
