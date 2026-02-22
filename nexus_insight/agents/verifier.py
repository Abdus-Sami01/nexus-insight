import logging
import json
from typing import List, Dict, Any, Optional
from nexus_insight.cognition.state import Claim, RawSource, Contradiction, ContradictionSeverity
from nexus_insight.cognition.prompts import Prompts
from nexus_insight.infra.llm_router import LLMRouter

logger = logging.getLogger(__name__)

class ChainOfVerificationVerifier:
    """
    Implements the 4-phase Chain-of-Verification (CoV) pattern.
    """

    def __init__(self, llm_router: LLMRouter):
        self.llm_router = llm_router

    async def extract_claims(self, sources: List[RawSource]) -> List[Claim]:
        """PHASE 1: Atomic Claim Extraction"""
        all_claims = []
        llm = await self.llm_router.get_llm("reasoning")
        
        for source in sources:
            if not source.content:
                continue
                
            prompt = Prompts.CLAIM_EXTRACTION_PROMPT + f"\n\nSource Content: {source.content[:10000]}"
            try:
                response = await llm.ainvoke(prompt)
                data = json.loads(response.content)
                for c in data.get("claims", []):
                    all_claims.append(Claim(
                        id=f"claim-{hash(c['content'])}",
                        content=c["content"],
                        source_id=source.id,
                        confidence=c.get("confidence", 0.5),
                        supporting_quotes=c.get("quotes", [])
                    ))
            except Exception as e:
                logger.error(f"Claim extraction failed for source {source.id}: {e}")
                
        return all_claims

    async def verify_claims(self, claims: List[Claim], sources: List[RawSource]) -> tuple[List[Claim], List[Contradiction]]:
        """PHASES 2, 3, & 4: Question Gen, Independent Verif, Final Decision"""
        verified_claims = []
        contradictions = []
        llm_fast = await self.llm_router.get_llm("fast")
        llm_reasoning = await self.llm_router.get_llm("reasoning")
        
        source_map = {s.id: s for s in sources}

        for claim in claims:
            # Phase 2: Question Generation
            questions = await self._generate_questions(claim, llm_fast)
            
            source = source_map.get(claim.source_id)
            if not source:
                continue

            results = []
            for q in questions:
                # Phase 3: Independent Verification (Anti-anchoring)
                res = await self._verify_question(q, source.content, llm_reasoning)
                results.append(res)

            # Phase 4: Final Decision
            is_verified, updated_confidence, contradiction = self._decide(claim, results)
            
            claim.verified = is_verified
            claim.confidence = updated_confidence
            verified_claims.append(claim)
            
            if contradiction:
                contradictions.append(contradiction)
                
        return verified_claims, contradictions

    async def _generate_questions(self, claim: Claim, llm) -> List[str]:
        prompt = Prompts.VERIFICATION_QUESTION_PROMPT + f"\n\nClaim: {claim.content}"
        try:
            response = await llm.ainvoke(prompt)
            data = json.loads(response.content)
            return data.get("questions", [])
        except Exception:
            return [f"Is the following statement true according to the source? {claim.content}"]

    async def _verify_question(self, question: str, content: str, llm) -> Dict:
        prompt = f"<source_text>{content[:15000]}</source_text>\n<question>{question}</question>\n" + Prompts.INDEPENDENT_VERIFICATION_PROMPT
        try:
            response = await llm.ainvoke(prompt)
            return json.loads(response.content)
        except Exception:
            return {"answer": "UNCERTAIN", "justification": "Error during verification"}

    def _decide(self, claim: Claim, results: List[Dict]) -> tuple[bool, float, Optional[Contradiction]]:
        yes_count = sum(1 for r in results if r["answer"] == "YES")
        no_count = sum(1 for r in results if r["answer"] == "NO")
        uncertain_count = sum(1 for r in results if r["answer"] == "UNCERTAIN")
        
        total = len(results)
        if total == 0:
            return False, claim.confidence, None

        if no_count > 0:
            return False, max(0.0, claim.confidence - 0.2), Contradiction(
                claim_a_id=claim.id,
                claim_b_id="source-truth",
                description=f"Claim '{claim.content}' contradicted by independent verification: {results}",
                severity=ContradictionSeverity.HIGH if no_count > 1 else ContradictionSeverity.MEDIUM
            )
        
        if yes_count == total:
            return True, min(1.0, claim.confidence + 0.3), None
            
        return False, claim.confidence, None
