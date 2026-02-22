import logging
from typing import Dict, List
from nexus_insight.cognition.state import ThoughtEntry
from datetime import datetime

logger = logging.getLogger(__name__)

class CostTracker:
    """
    Token usage tracker (no real money billing, just stats for optimization).
    Uses tiktoken for estimation if the model doesn't return usage metadata.
    """
    
    def __init__(self):
        self._total_tokens = 0
        self._usage_by_model: Dict[str, int] = {}

    def track_usage(self, model_name: str, tokens: int):
        self._total_tokens += tokens
        self._usage_by_model[model_name] = self._usage_by_model.get(model_name, 0) + tokens
        logger.info(f"Usage update: {model_name} +{tokens} tokens. Total: {self._total_tokens}")

    def get_summary(self) -> Dict:
        return {
            "total_tokens": self._total_tokens,
            "usage_by_model": self._usage_by_model,
            "estimated_cost_usd": 0.0  # It's free!
        }

def create_thought_entry(node: str, thought: str, tokens: int, backend: str) -> ThoughtEntry:
    return ThoughtEntry(
        timestamp=datetime.now(),
        node=node,
        thought=thought,
        tokens_used=tokens,
        llm_backend=backend
    )
