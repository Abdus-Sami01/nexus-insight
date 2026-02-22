import pytest
from unittest.mock import AsyncMock, MagicMock
from nexus_insight.agents.orchestrator import Orchestrator

@pytest.mark.asyncio
async def test_full_graph_execution():
    """
    Tests the LangGraph orchestrator state machine flow.
    Mocks out ALL external LLM/Network calls to ensure deterministic local testing.
    """
    # 1. Setup global mocks
    mock_router = MagicMock()
    mock_router.get_llm = AsyncMock()
    
    # Sequence of mock LLM responses passing through the graph
    mock_llm = AsyncMock()
    mock_llm.ainvoke.side_effect = [
        MagicMock(content='{"sanitized_query": "mock query", "intent": "factual"}'), # intake
        MagicMock(content='{"sub_queries": ["mock search 1", "mock search 2"]}'),     # plan
        MagicMock(content='Synthetic response')                                        # synthesize
    ]
    mock_router.get_llm.return_value = mock_llm
    
    mock_researcher = AsyncMock()
    mock_researcher.explore.return_value = [] # Return empty sources to force fast-fail logic
    
    mock_verifier = AsyncMock()
    mock_verifier.extract_claims.return_value = []
    mock_verifier.verify_claims.return_value = ([], []) # (verified_dossier, contradictions)
    
    mock_debater = AsyncMock()
    mock_debater.resolve_conflicts.return_value = [{"role":"Proposer", "content":"No data."}]
    
    mock_graph_extractor = AsyncMock()
    mock_graph_extractor.extract_and_build.return_value = "Mocked Graph Summary"
    
    mock_evaluator = AsyncMock()
    mock_evaluator.evaluate.return_value = {"score": 1.0}
    
    # 2. Instantiate Orchestrator with Mocks
    orch = Orchestrator(
        llm_router=mock_router, 
        researcher=mock_researcher, 
        verifier=mock_verifier, 
        debater=mock_debater,
        graph_extractor=mock_graph_extractor,
        evaluator=mock_evaluator
    )
    
    # 3. Fire initial state
    initial_state = {
        "query": "Who is the CEO of Google?",
        "session_id": "test-session",
        "revision_count": 0,
        "max_revisions": 1,
        "confidence_threshold": 0.8,
        "thought_log": [],
        "raw_sources": [],
        "extracted_claims": [],
        "contradictions": [],
        "verified_dossier": [],
        "debate_log": [],
        "query_refinements": [],
        "citations": [],
        "llm_backend_used": [],
        "span_ids": [],
        "total_tokens_used": 0,
        "token_budget": 10000,
        "budget_exceeded": False,
        "confidence_score": 0.0,
        "faithfulness_score": 0.0,
        "trace_id": "test-trace",
        "current_node": "START",
        "structured_output": {}
    }
    
    # 4. Assert graph traverses end-to-end without unhandled exceptions
    result = await orch.graph.ainvoke(initial_state)
    
    assert result["session_id"] == "test-session"
    assert "mock query" in result["query"]
    assert result["graph_summary"] == "Mocked Graph Summary"
    assert result["final_report"] == "Synthetic response"
    assert result["faithfulness_score"] == 1.0
    assert result["current_node"] == "END"
