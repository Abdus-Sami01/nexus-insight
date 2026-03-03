import pytest
from nexus_insight.cognition.embeddings import LocalEmbedder

@pytest.fixture
def embedder():
    return LocalEmbedder()

def test_embed_documents(embedder):
    docs = ["This is a test document.", "Another test document about quantum physics."]
    embeddings = embedder.embed_documents(docs)
    assert len(embeddings) == 2
    assert len(embeddings[0]) > 0
    assert isinstance(embeddings[0][0], float)

def test_embed_query(embedder):
    query = "What is the capital of France?"
    embedding = embedder.embed_query(query)
    assert len(embedding) > 0
    assert isinstance(embedding[0], float)

def test_get_dimension(embedder):
    dim = embedder.get_dimension()
    assert dim > 0
    assert isinstance(dim, int)

def test_get_model_info(embedder):
    info = embedder.get_model_info()
    assert "model" in info
    assert "dimension" in info
    assert "device" in info
