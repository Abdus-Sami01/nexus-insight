import logging
import json
import re
from typing import List, Dict
from nexus_insight.cognition.state import Claim
from nexus_insight.cognition.prompts import Prompts
from nexus_insight.infra.llm_router import LLMRouter

logger = logging.getLogger(__name__)

class FaithfulnessEvaluator:
    """
    RAGAS-inspired, fully local faithfulness evaluation.
    """

    def __init__(self, llm_router: LLMRouter):
        self.llm_router = llm_router

    async def evaluate(self, report: str, verified_dossier: List[Claim]) -> Dict:
        """
        Calculates faithfulness score based on report content vs verified claims.
        """
        if not report or not verified_dossier:
            return {"score": 0.0, "unsupported": [], "contradicted": []}

        sentences = self._split_into_sentences(report)
        llm_reasoning = await self.llm_router.get_llm("reasoning")
        
        claims_text = "\n".join([f"- {c.content}" for c in verified_dossier])
        
        supported_count = 0
        unsupported = []
        contradicted = []

        for sentence in sentences:
            if len(sentence.split()) < 5: continue # Skip short sentences
            
            prompt = f"<verified_claims>\n{claims_text}\n</verified_claims>\n<sentence>{sentence}</sentence>\n" + Prompts.FAITHFULNESS_PROMPT
            
            try:
                response = await llm_reasoning.ainvoke(prompt)
                data = json.loads(response.content)
                verdict = data.get("verdict", "unsupported")
                
                if verdict == "supported":
                    supported_count += 1
                elif verdict == "contradicted":
                    contradicted.append(sentence)
                else:
                    unsupported.append(sentence)
            except Exception as e:
                logger.error(f"Faithfulness check failed for sentence: {sentence}. Error: {e}")
                unsupported.append(sentence)

        total = len(sentences) or 1
        score = supported_count / total
        
        return {
            "score": score,
            "unsupported": unsupported,
            "contradicted": contradicted
        }

    def _split_into_sentences(self, text: str) -> List[str]:
        # Simple regex split for sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
