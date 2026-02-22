import logging
from typing import List, Dict
from sentence_transformers import SentenceTransformer
from nexus_insight.config import settings

logger = logging.getLogger(__name__)

class LocalEmbedder:
    """
    Wraps sentence-transformers for local, free embedding generation.
    No API key required. Models downloaded once and cached locally.
    """
    
    def __init__(self):
        self._model = None
        self.model_name = settings.EMBEDDING_MODEL
        self.fallback_model_name = settings.EMBEDDING_FALLBACK

    def _load_model(self) -> SentenceTransformer:
        """Load on first call, cache in self._model"""
        if self._model is None:
            try:
                logger.info(f"Loading embedding model: {self.model_name}")
                self._model = SentenceTransformer(self.model_name)
            except Exception as e:
                logger.warning(f"Failed to load primary model {self.model_name}: {e}. Falling back to {self.fallback_model_name}")
                self._model = SentenceTransformer(self.fallback_model_name)
                self.model_name = self.fallback_model_name
        return self._model

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Batch embed with progress logging for large sets"""
        model = self._load_model()
        logger.info(f"Embedding {len(texts)} documents...")
        embeddings = model.encode(texts, batch_size=32, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> List[float]:
        """Single query embedding, normalized"""
        model = self._load_model()
        embedding = model.encode([text], normalize_embeddings=True)[0]
        return embedding.tolist()

    def get_dimension(self) -> int:
        """Return embedding dimension for FAISS index init"""
        model = self._load_model()
        return model.get_sentence_embedding_dimension()

    def get_model_info(self) -> Dict:
        """Return model name, dimension, device for health endpoint"""
        model = self._load_model()
        return {
            "model": self.model_name,
            "dimension": self.get_dimension(),
            "device": str(model.device)
        }
