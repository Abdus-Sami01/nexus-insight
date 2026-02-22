import logging
import uuid
import json
from datetime import datetime
from typing import Dict, List, Literal, Optional, Any
from langgraph.graph import StateGraph, START, END
from nexus_insight.cognition.state import ResearchState, RawSource, Claim, Citation, ThoughtEntry
from nexus_insight.cognition.prompts import Prompts
from nexus_insight.infra.llm_router import LLMRouter
from nexus_insight.infra.otel import trace_node
from nexus_insight.agents.researcher import ResearcherAgent
from nexus_insight.agents.verifier import ChainOfVerificationVerifier
from nexus_insight.agents.debater import MultiAgentDebater
from nexus_insight.cognition.graph import GraphExtractor
from nexus_insight.evaluation.faithfulness import FaithfulnessEvaluator
from nexus_insight.config import settings

logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(
        self, 
        llm_router: LLMRouter,
        researcher: ResearcherAgent,
        verifier: ChainOfVerificationVerifier,
        debater: MultiAgentDebater,
        graph_extractor: GraphExtractor,
        evaluator: FaithfulnessEvaluator
    ):
        self.llm_router = llm_router
        self.researcher = researcher
        self.verifier = verifier
        self.debater = debater
        self.graph_extractor = graph_extractor
        self.evaluator = evaluator
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(ResearchState)

        workflow.add_node("intake", self.node_intake)
        workflow.add_node("plan", self.node_plan)
        workflow.add_node("explore", self.node_explore)
        workflow.add_node("analyze", self.node_analyze)
        workflow.add_node("verify", self.node_verify)
        workflow.add_node("refine", self.node_refine)
        workflow.add_node("build_graph", self.node_build_graph)
        workflow.add_node("debate", self.node_debate)
        workflow.add_node("synthesize", self.node_synthesize)
        workflow.add_node("evaluate", self.node_evaluate)
        workflow.add_node("finalize", self.node_finalize)

        workflow.add_edge(START, "intake")
        workflow.add_edge("intake", "plan")
        workflow.add_edge("plan", "explore")
        workflow.add_edge("explore", "analyze")
        workflow.add_edge("analyze", "verify")
        
        workflow.add_conditional_edges(
            "verify",
            self.should_verify_continue,
            {
                "continue": "refine",
                "stop": "build_graph"
            }
        )
        
        workflow.add_edge("refine", "explore")
        workflow.add_edge("build_graph", "debate")
        workflow.add_edge("debate", "synthesize")
        workflow.add_edge("synthesize", "evaluate")
        
        workflow.add_conditional_edges(
            "evaluate",
            self.should_evaluate_continue,
            {
                "continue": "verify",
                "stop": "finalize"
            }
        )
        
        workflow.add_edge("finalize", END)

        return workflow.compile()

    @trace_node("intake")
    async def node_intake(self, state: ResearchState) -> Dict:
        llm = await self.llm_router.get_llm("fast")
        prompt = Prompts.INTAKE_PROMPT + f"\n\nUser Query: {state['query']}"
        response = await llm.ainvoke(prompt)
        try:
            data = json.loads(response.content)
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Failed to parse intake response: {response.content[:100]}")
            data = {"intent": "factual", "sanitized_query": state['query']}
        
        return {
            "intent_classification": data["intent"],
            "query": data["sanitized_query"],
            "llm_backend_used": [response.response_metadata.get("model_name", "unknown")],
            "thought_log": [ThoughtEntry(
                timestamp=datetime.now(),
                node="intake",
                thought=f"Classified intent as {data['intent']}",
                tokens_used=response.response_metadata.get("token_usage", {}).get("total_tokens", 0),
                llm_backend="groq"
            )]
        }

    @trace_node("plan")
    async def node_plan(self, state: ResearchState) -> Dict:
        llm = await self.llm_router.get_llm("fast")
        prompt = Prompts.PLANNING_PROMPT + f"\n\nQuery: {state['query']}"
        response = await llm.ainvoke(prompt)
        try:
            data = json.loads(response.content)
            sub_queries = data.get("sub_queries", [state["query"]])
        except (json.JSONDecodeError, TypeError):
            sub_queries = [state["query"]]
            
        return {"query_refinements": sub_queries}

    @trace_node("explore")
    async def node_explore(self, state: ResearchState) -> Dict:
        modalities = state.get("structured_output", {}).get("modalities", ["web"])
        sources = await self.researcher.explore(
            queries=state["query_refinements"],
            modalities=modalities,
            pdf_urls=state.get("structured_output", {}).get("pdf_urls"),
            video_urls=state.get("structured_output", {}).get("video_urls")
        )
        return {"raw_sources": sources}

    @trace_node("analyze")
    async def node_analyze(self, state: ResearchState) -> Dict:
        claims = await self.verifier.extract_claims(state["raw_sources"])
        return {"extracted_claims": claims}

    @trace_node("verify")
    async def node_verify(self, state: ResearchState) -> Dict:
        verified, contr = await self.verifier.verify_claims(state["extracted_claims"], state["raw_sources"])
        
        # Calculate confidence
        verified_count = sum(1 for c in verified if c.verified)
        total_count = len(verified)
        
        if total_count == 0:
            # No sources were fetched — report is LLM knowledge-based, not empirically verified
            conf_score = -1.0  # sentinel: means "not applicable"
        else:
            conf_score = verified_count / total_count

        return {
            "verified_dossier": verified,
            "contradictions": contr,
            "confidence_score": conf_score,
            "revision_count": state["revision_count"] + 1
        }

    def should_verify_continue(self, state: ResearchState) -> str:
        # Always stop if max revisions hit
        if state["revision_count"] >= state["max_revisions"]:
            return "stop"
        # Stop immediately if we have no sources (nothing to refine against)
        if not state["raw_sources"]:
            return "stop"
        # Continue refining only if confidence is truly low AND we have something to work with
        if state["confidence_score"] < state["confidence_threshold"] and state["verified_dossier"]:
            return "continue"
        return "stop"

    @trace_node("refine")
    async def node_refine(self, state: ResearchState) -> Dict:
        """Generate targeted follow-up queries based on what's missing."""
        llm = await self.llm_router.get_llm("fast")
        contradictions_text = "; ".join([c.description[:80] for c in state["contradictions"]]) or "none"
        low_conf = [c.content[:60] for c in state["verified_dossier"] if not c.verified]
        low_conf_text = "; ".join(low_conf[:3]) or "none"
        
        prompt = (
            f"You are a research assistant. Generate exactly 2 short, specific web search queries "
            f"to fill in missing information for a research task about: '{state['query']}'.\n"
            f"Contradictions found: {contradictions_text}\n"
            f"Unverified claims: {low_conf_text}\n"
            f"Return ONLY a JSON object: {{\"queries\": [\"query1\", \"query2\"]}}"
        )
        try:
            response = await llm.ainvoke(prompt)
            data = json.loads(response.content)
            new_queries = [q.strip() for q in data.get("queries", []) if isinstance(q, str) and q.strip()]
        except Exception:
            # Fallback: just re-search the original query
            new_queries = [state["query"]]
        
        return {"query_refinements": new_queries[:2]}

    @trace_node("build_graph")
    async def node_build_graph(self, state: ResearchState) -> Dict:
        """Constructs a semantic Knowledge Graph from the extracted sources."""
        summary = await self.graph_extractor.extract_and_build(state.get("raw_sources", []), state["query"])
        return {
            "graph_summary": summary,
            "thought_log": [ThoughtEntry(
                timestamp=datetime.now(),
                node="build_graph",
                thought=f"Graph constructed. Summary length: {len(summary)} chars.",
                tokens_used=0,
                llm_backend="groq"
            )]
        }

    @trace_node("debate")
    async def node_debate(self, state: ResearchState) -> Dict:
        """Runs the adversarial Proposer/Skeptic debate over contradictions and unverified claims."""
        # Unverified claims are those in verified_dossier with verified=False
        unverified = [c for c in state.get("verified_dossier", []) if not c.verified]
        contradictions = state.get("contradictions", [])
        
        log = await self.debater.resolve_conflicts(state["query"], unverified, contradictions)
        return {
            "debate_log": log,
            "thought_log": [ThoughtEntry(
                timestamp=datetime.now(),
                node="debate",
                thought=f"Debate completed. {len(log)} turns logged.",
                tokens_used=0,
                llm_backend="groq"
            )]
        }

    @trace_node("synthesize")
    async def node_synthesize(self, state: ResearchState) -> Dict:
        llm = await self.llm_router.get_llm("reasoning")
        claims_text = "\n".join([f"- {c.content} [Source: {c.source_id}]" for c in state["verified_dossier"] if c.verified])
        
        # Inject Advanced AI context
        advanced_context = ""
        if state.get("graph_summary"):
            advanced_context += f"\n--- KNOWLEDGE GRAPH CONTEXT ---\n{state['graph_summary']}\n"
        if state.get("debate_log"):
            advanced_context += "\n--- ADVERSARIAL DEBATE LOG ---\n"
            for turn in state["debate_log"]:
                advanced_context += f"**{turn['role']}**: {turn['content']}\n"
                
        prompt = Prompts.SYNTHESIS_PROMPT + f"\n\nVerified Claims:\n{claims_text}\n{advanced_context}\nQuery: {state['query']}"
        response = await llm.ainvoke(prompt)
        return {"final_report": response.content}

    @trace_node("evaluate")
    async def node_evaluate(self, state: ResearchState) -> Dict:
        eval_result = await self.evaluator.evaluate(state["final_report"], state["verified_dossier"])
        return {"faithfulness_score": eval_result["score"]}

    def should_evaluate_continue(self, state: ResearchState) -> str:
        # If faithfulness is very low, go back to verify (re-extract or re-verify)
        # But for now, we usually stop unless it's a disaster
        if state.get("faithfulness_score", 1.0) < settings.FAITHFULNESS_THRESHOLD and state["revision_count"] < state["max_revisions"]:
            return "continue"
        return "stop"

    @trace_node("finalize")
    async def node_finalize(self, state: ResearchState) -> Dict:
        # Format citations
        citations = []
        for s in state["raw_sources"]:
            citations.append(Citation(
                source_id=s.id,
                title=s.metadata.get("title", "Unknown"),
                url=s.url,
                access_date=datetime.now().date(),
                formatted_citation=f"{s.metadata.get('title', 'Unknown')}. Retrieved from {s.url}"
            ))
        return {"citations": citations, "current_node": "END"}
