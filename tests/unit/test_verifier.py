import pytest
from unittest.mock import AsyncMock, patch
from nexus_insight.agents.verifier import ChainOfVerificationVerifier
from nexus_insight.cognition.state import RawSource, SourceType, Claim

@pytest.fixture
def mock_router():
    router = AsyncMock()
    
    # Mock LLM behavior
    llm = AsyncMock()
    
    async def mock_ainvoke(prompt, **kwargs):
        res = AsyncMock()
        if "Atomic Claim Extraction" in prompt or "fact extraction" in prompt.lower():
            res.content = '{"claims": [{"content": "The sky is blue", "confidence": 0.9, "quotes": ["sky is blue"]}, {"content": "Water is wet", "confidence": 0.9, "quotes": ["water is wet"]}]}'
        elif "verification questions" in prompt.lower() or "VERIFICATION_QUESTION_PROMPT" in prompt:
            res.content = '{"questions": ["Is the sky blue?", "Is the atmosphere clear?"]}'
        elif "independent fact verifier" in prompt.lower() or "INDEPENDENT_VERIFICATION_PROMPT" in prompt:
            res.content = '{"answer": "YES", "justification": "The text confirms it", "quote": "sky is blue"}'
        else:
            res.content = '{"content": "default response"}'
        return res

    llm.ainvoke.side_effect = mock_ainvoke
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

@pytest.fixture
def other_source():
    from datetime import datetime
    return RawSource(
        id="src2",
        source_type=SourceType.WEB,
        url="http://example2.com",
        content="The sky is blue indeed.",
        metadata={},
        trust_score=0.9,
        fetched_at=datetime.now()
    )

@pytest.mark.asyncio
async def test_extract_claims(mock_router, dummy_source):
    verifier = ChainOfVerificationVerifier(mock_router)
    claims = await verifier.extract_claims([dummy_source])
    
    assert len(claims) == 2
    assert "sky" in claims[0].content or "sky" in claims[1].content
    assert claims[0].source_id == "src1"

@pytest.mark.asyncio
async def test_verify_claims_cross_verification(mock_router, dummy_source, other_source):
    verifier = ChainOfVerificationVerifier(mock_router)
    claim_to_verify = Claim(
        id="c1",
        content="The sky is blue",
        source_id="src1", # Originates from src1
        confidence=0.5,
        supporting_quotes=[]
    )
    
    # We provide both sources. Verification should use other_source since it's not the origin.
    verified_claims, contradictions = await verifier.verify_claims([claim_to_verify], [dummy_source, other_source])
    
    assert len(verified_claims) == 1
    assert verified_claims[0].verified is True
    assert verified_claims[0].confidence > 0.5
    assert len(contradictions) == 0
