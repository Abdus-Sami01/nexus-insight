import uuid
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sse_starlette.sse import EventSourceResponse
from nexus_insight.api.schemas import ResearchRequest, FinalReport, SSEEvent
from nexus_insight.api.auth import validate_api_key
from nexus_insight.api.streaming import sse_generator
from nexus_insight.cognition.state import ResearchState
from nexus_insight.agents.orchestrator import Orchestrator
from nexus_insight.infra.llm_router import LLMRouter
from nexus_insight.infra.cost_tracker import CostTracker
from nexus_insight.cognition.memory import MemoryManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["research"])

# These would typically be injected via a dependency injection framework
# For this implementation, we assume they are initialized and available
_orchestrator: Optional[Orchestrator] = None
_llm_router = LLMRouter()
_memory_manager = MemoryManager()

def set_orchestrator(orch: Orchestrator):
    global _orchestrator
    _orchestrator = orch

@router.post("/research")
async def start_research(
    request: ResearchRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(validate_api_key)
):
    if not _orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    session_id = str(uuid.uuid4())
    
    initial_state: ResearchState = {
        "query": request.query,
        "session_id": session_id,
        "intent_classification": "factual",
        "raw_sources": [],
        "source_priority": [],
        "extracted_claims": [],
        "contradictions": [],
        "verified_dossier": [],
        "revision_count": 0,
        "max_revisions": 5,
        "query_refinements": [],
        "total_tokens_used": 0,
        "token_budget": 200000,
        "budget_exceeded": False,
        "confidence_score": 0.0,
        "confidence_threshold": request.confidence_threshold,
        "faithfulness_score": 1.0,
        "llm_backend_used": [],
        "trace_id": session_id,
        "span_ids": [],
        "thought_log": [],
        "current_node": "START",
        "final_report": None,
        "citations": [],
        "structured_output": {
            "modalities": request.modalities,
            "pdf_urls": [str(u) for u in request.pdf_urls] if request.pdf_urls else [],
            "video_urls": [str(u) for u in request.video_urls] if request.video_urls else []
        }
    }

    if request.stream:
        return EventSourceResponse(sse_generator(_run_research_stream(initial_state)))
    else:
        # Non-streaming implementation would await full execution
        result = await _orchestrator.graph.ainvoke(initial_state)
        _memory_manager.save_session(result)
        return result

async def _run_research_stream(state: ResearchState):
    """
    Adapter that runs the LangGraph and yields SSE events.
    """
    try:
        async for output in _orchestrator.graph.astream(state, stream_mode="updates"):
            # Map LangGraph updates to SSE events
            node_name = list(output.keys())[0]
            node_data = output[node_name]
            
            if "thought_log" in node_data and node_data["thought_log"]:
                yield SSEEvent(event="thought", data=node_data["thought_log"][-1])
            
            if "raw_sources" in node_data:
                for s in node_data["raw_sources"]:
                    yield SSEEvent(event="source", data={"id": s.id, "type": s.source_type, "url": s.url})
            
            yield SSEEvent(event="progress", data={"node": node_name, "backend": "groq"})
            
            if node_name == "finalize":
                yield SSEEvent(event="result", data={
                    "report": node_data.get("final_report"),
                    "citations": [c.model_dump() for c in node_data.get("citations", [])]
                })

    except Exception as e:
        logger.error(f"Error in research stream: {e}")
        yield SSEEvent(event="error", data={"message": str(e)})

@router.get("/session/{session_id}")
async def get_session(session_id: str, api_key: str = Depends(validate_api_key)):
    session = _memory_manager.load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "backends": await _llm_router.get_backend_info()
    }
