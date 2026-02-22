import pytest
from unittest.mock import AsyncMock, patch
from nexus_insight.agents.verifier import ChainOfVerificationVerifier
from nexus_insight.cognition.state import RawSource, SourceType, Claim

@pytest.fixture
def mock_router():
    router = AsyncMock()
    
    # Mock LLM for claim extraction
    llm = AsyncMock()
    llm.ainvoke.return_value.content = '{"claims": ["The sky is blue", "Water is wet"]}'
    router.get_llm.return_value = llm
    return router

@pytest.fixture
def dummy_source():
    from datetime import datetime
    return RawSource(
        id="src1",
        source_type=SourceType.WEB,
        url="http://example.com",
        content="The sky is blue and water is wet.",
        metadata={},
        trust_score=0.9,
        fetched_at=datetime.now()
    )

@pytest.mark.asyncio
async def test_extract_claims(mock_router, dummy_source):
    verifier = ChainOfVerificationVerifier(mock_router)
    claims = await verifier.extract_claims([dummy_source])
    
    assert len(claims) == 2
    assert claims[0].content == "The sky is blue"
    assert claims[1].content == "Water is wet"
    assert claims[0].source_id == "src1"

@pytest.mark.asyncio
async def test_verify_claims_no_contradiction(mock_router, dummy_source):
    # Setup mock for verification step
    llm = AsyncMock()
    llm.ainvoke.return_value.content = '{"is_supported": true, "confidence": 0.95, "supporting_quotes": ["The sky is blue"]}'
    mock_router.get_llm.return_value = llm

    verifier = ChainOfVerificationVerifier(mock_router)
    claim_to_verify = Claim(
        id="c1",
        content="The sky is blue",
        source_id="src1",
        confidence=0.0,
        supporting_quotes=[]
    )
    
    verified_claims, contradictions = await verifier.verify_claims([claim_to_verify], [dummy_source])
    
    assert len(verified_claims) == 1
    assert verified_claims[0].verified is True
    assert verified_claims[0].confidence == 0.95
    assert len(contradictions) == 0
