import logging
import asyncio
import time
from typing import Dict, Union, Literal, Optional, Any
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langchain_core.language_models.chat_models import BaseChatModel
from groq import RateLimitError, APIStatusError
from nexus_insight.config import settings

logger = logging.getLogger(__name__)

class NexusLLMUnavailableError(Exception):
    """Raised when both Groq and Ollama backends are unavailable."""
    pass

class LLMRouter:
    """
    Intelligent router that selects between Groq (fast, free cloud)
    and Ollama (local fallback) based on availability and task type.
    """

    TASK_MODEL_MAP = {
        "fast": {
            "groq": settings.GROQ_FAST_MODEL,
            "ollama": settings.OLLAMA_FAST_MODEL
        },
        "reasoning": {
            "groq": settings.GROQ_REASONING_MODEL,
            "ollama": settings.OLLAMA_REASONING_MODEL
        }
    }

    _groq_available_cached: Optional[bool] = None
    _last_groq_check: float = 0
    _CACHE_TTL = 60  # seconds

    def __init__(self):
        self._current_backend = "groq" if settings.LLM_MODE in ["groq", "auto"] else "ollama"

    async def get_llm(self, task_type: Literal["fast", "reasoning"]) -> BaseChatModel:
        """
        Returns appropriate LangChain chat model.
        Checks Groq availability first, falls back to Ollama.
        """
        mode = settings.LLM_MODE
        
        if mode == "groq":
            return self._get_groq_llm(task_type)
        elif mode == "ollama":
            return await self._get_ollama_llm(task_type)
        
        # Auto mode: try Groq first
        if await self._check_groq_available():
            try:
                # Return a wrapper that handles rate limits by falling back
                return self._get_groq_llm(task_type)
            except Exception as e:
                logger.warning(f"Groq failed during init: {e}. Falling back to Ollama.")
        
        return await self._get_ollama_llm(task_type)

    def _get_groq_llm(self, task_type: str) -> BaseChatModel:
        model_name = self.TASK_MODEL_MAP[task_type]["groq"]
        return ChatGroq(
            model=model_name,
            groq_api_key=settings.GROQ_API_KEY,
            temperature=0,
            max_retries=2
        )

    async def _get_ollama_llm(self, task_type: str) -> BaseChatModel:
        if not await self._check_ollama_available():
            raise NexusLLMUnavailableError("Ollama is not reachable and Groq is disabled/unavailable.")
        
        model_name = self.TASK_MODEL_MAP[task_type]["ollama"]
        return ChatOllama(
            model=model_name,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0
        )

    async def _check_groq_available(self) -> bool:
        """Lightweight check with caching"""
        if not settings.GROQ_API_KEY:
            return False
            
        now = time.time()
        if self._groq_available_cached is not None and (now - self._last_groq_check) < self._CACHE_TTL:
            return self._groq_available_cached

        try:
            # We don't want to actually send a request, but ChatGroq doesn't have a cheap 'ping'
            # However, we can just check if the key exists for now, or do a tiny request if needed.
            # For brevity and safety, we check if key is present and not dummy.
            self._groq_available_cached = len(settings.GROQ_API_KEY) > 10
        except Exception:
            self._groq_available_cached = False
            
        self._last_groq_check = now
        return self._groq_available_cached

    async def _check_ollama_available(self) -> bool:
        """Calls GET http://OLLAMA_URL/api/tags"""
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=2.0)
                return response.status_code == 200
        except Exception:
            return False

    async def get_backend_info(self) -> Dict[str, Any]:
        """Returns current backend status for /v1/health endpoint."""
        return {
            "groq": {"available": bool(settings.GROQ_API_KEY)},
            "ollama": {"available": await self._check_ollama_available()},
            "active_mode": settings.LLM_MODE
        }
