import pytest
from nexus_insight.cognition.embeddings import LocalEmbedder

@pytest.fixture
def embedder():
    return LocalEmbedder(model_name="all-MiniLM-L6-v2") # Use smaller model for fast tests

def test_embed_documents(embedder):
    docs = ["This is a test document.", "Another test document about quantum physics."]
    idx = embedder.create_index(docs)
    assert idx is not None
    assert idx in embedder.indices
    assert embedder.indices[idx].ntotal == 2

def test_similarity_search(embedder):
    docs = [
        "The capital of France is Paris.",
        "Quantum computing uses qubits.",
        "Python is a programming language."
    ]
    idx = embedder.create_index(docs)
    
    # Search for France
    results = embedder.search(idx, "What is the capital of France?", k=1)
    assert len(results) == 1
    assert "Paris" in results[0]["document"]
    assert results[0]["distance"] < 1.0 # arbitrary threshold for cosine/L2
    
def test_search_invalid_index(embedder):
    with pytest.raises(ValueError):
        embedder.search("invalid-idx", "query", k=1)
