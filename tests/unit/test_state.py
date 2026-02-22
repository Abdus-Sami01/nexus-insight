import pytest
from datetime import datetime
from pydantic import ValidationError
from nexus_insight.cognition.state import RawSource, SourceType, Claim, Contradiction, ContradictionSeverity

def test_raw_source_validation():
    # Valid source
    source = RawSource(
        id="test-1",
        source_type=SourceType.WEB,
        url="https://example.com",
        content="Test content",
        metadata={"title": "Test"},
        trust_score=0.8,
        fetched_at=datetime.now()
    )
    assert source.id == "test-1"
    assert source.trust_score == 0.8
    assert source.source_type == SourceType.WEB

    # Invalid sources
    with pytest.raises(ValidationError):
        RawSource(
            id="test-2",
            source_type=SourceType.WEB,
            url="https://example.com",
            content="Test content",
            metadata={},
            trust_score=1.5, # Out of bounds
            fetched_at=datetime.now()
        )

def test_claim_validation():
    claim = Claim(
        id="claim-1",
        content="The earth is round.",
        source_id="test-1",
        confidence=0.9,
        supporting_quotes=["It's a sphere"]
    )
    assert claim.verified is False
    assert claim.confidence == 0.9

    with pytest.raises(ValidationError):
        Claim(
            id="claim-2",
            content="Too confident.",
            source_id="test-1",
            confidence=1.1, # Out of bounds
            supporting_quotes=[]
        )

def test_contradiction_validation():
    c = Contradiction(
        claim_a_id="c1",
        claim_b_id="c2",
        description="Conflicts on shape.",
        severity=ContradictionSeverity.HIGH
    )
    assert c.severity == ContradictionSeverity.HIGH
    assert c.claim_a_id == "c1"
