import logging
from typing import List, Dict, Optional
from pydantic import BaseModel
from nexus_insight.cognition.state import Claim, Contradiction
from nexus_insight.infra.llm_router import LLMRouter
from nexus_insight.infra.otel import trace_node

logger = logging.getLogger(__name__)

class DebateParticipant:
    def __init__(self, name: str, persona: str, llm_router: LLMRouter):
        self.name = name
        self.persona = persona
        self.llm_router = llm_router

    async def speak(self, topic: str, context: str, history: List[Dict[str, str]]) -> str:
        llm = await self.llm_router.get_llm("fast")
        
        history_text = ""
        for turn in history:
            history_text += f"**{turn['role']}**: {turn['content']}\n\n"

        prompt = (
            f"You are the {self.name}.\n"
            f"Persona: {self.persona}\n\n"
            f"The topic under debate is: '{topic}'\n"
            f"Available Evidence Context: {context}\n\n"
            f"Debate History:\n{history_text}\n"
            f"It is your turn to speak. Provide a concise, rigorous argument (under 100 words).\n"
            f"If you agree a truth has been reached, state '[CONCEDE]'. Otherwise, present your counter-claim."
        )

        try:
            response = await llm.ainvoke(prompt)
            return response.content.strip()
        except Exception as e:
            logger.error(f"Debate participant {self.name} failed: {e}")
            return f"[ERROR] Failed to formulate argument."

class MultiAgentDebater:
    def __init__(self, llm_router: LLMRouter):
        self.proposer = DebateParticipant(
            name="Proposer",
            persona="You argue for the synthesis of the claims, trying to find a unified truth even if sources slightly differ. You are optimistic about the data.",
            llm_router=llm_router
        )
        self.skeptic = DebateParticipant(
            name="Skeptic",
            persona="You are deeply cynical. You aggressively point out logical flaws, missing evidence, or contradictions. You demand definitive proof before accepting any synthesis.",
            llm_router=llm_router
        )
        self.max_turns = 2  # 2 turns per agent = 4 total messages

    @trace_node("debate_resolution")
    async def resolve_conflicts(
        self, 
        query: str,
        unverified_claims: List[Claim], 
        contradictions: List[Contradiction]
    ) -> List[Dict[str, str]]:
        """
        Runs an adversarial debate over unverified claims and contradictions.
        Returns the debate log transcript.
        """
        if not unverified_claims and not contradictions:
            return [{"role": "System", "content": "No conflicts or low-confidence claims found; debate skipped."}]
            
        topic = f"Query: {query}\n"
        if contradictions:
            topic += "We found direct contradictions in the sources:\n"
            for c in contradictions[:2]:  # Focus on top 2
                topic += f"- {c.description} (Severity: {c.severity})\n"
        
        if unverified_claims:
            topic += "We have unverified claims hanging in the dossier:\n"
            for u in unverified_claims[:3]: # Focus on top 3
                topic += f"- {u.content}\n"

        history: List[Dict[str, str]] = []
        
        for turn in range(self.max_turns):
            # Proposer goes first
            prop_msg = await self.proposer.speak(topic=topic, context="See history.", history=history)
            history.append({"role": "Proposer", "content": prop_msg})
            if "[CONCEDE]" in prop_msg:
                break
                
            # Skeptic responds
            skep_msg = await self.skeptic.speak(topic=topic, context="See history.", history=history)
            history.append({"role": "Skeptic", "content": skep_msg})
            if "[CONCEDE]" in skep_msg:
                break

        return history
