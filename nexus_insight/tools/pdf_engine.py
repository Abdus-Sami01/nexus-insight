import os
import logging
import fitz  # PyMuPDF
import faiss
import numpy as np
import httpx
from datetime import datetime
from typing import List, Optional, Dict
from langchain.text_splitter import RecursiveCharacterTextSplitter
from nexus_insight.cognition.state import RawSource, SourceType
from nexus_insight.cognition.embeddings import LocalEmbedder
from nexus_insight.config import settings

logger = logging.getLogger(__name__)

class PDFEngine:
    """
    PDF engine for extraction, chunking, and local vector indexing.
    """

    def __init__(self, embedder: LocalEmbedder):
        self.embedder = embedder
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800, 
            chunk_overlap=100
        )
        self.indices: Dict[str, faiss.Index] = {}
        self.chunk_store: Dict[str, List[str]] = {}

    async def process_source(self, url_or_path: str) -> RawSource:
        """Download (if needed) and extract content from PDF"""
        try:
            content = ""
            metadata = {}
            
            if url_or_path.startswith("http"):
                local_path = f"/tmp/nexus_{hash(url_or_path)}.pdf"
                async with httpx.AsyncClient() as client:
                    response = await client.get(url_or_path, timeout=settings.TIMEOUT_PDF)
                    with open(local_path, "wb") as f:
                        f.write(response.content)
            else:
                local_path = url_or_path

            doc = fitz.open(local_path)
            metadata = {
                "title": doc.metadata.get("title", "Unknown"),
                "author": doc.metadata.get("author", "Unknown"),
                "pages": len(doc)
            }
            
            full_text = []
            for page in doc:
                full_text.append(page.get_text())
            
            content = "\n\n".join(full_text)
            
            source_id = f"pdf-{hash(url_or_path)}"
            await self._index_content(source_id, content)

            return RawSource(
                id=source_id,
                source_type=SourceType.PDF,
                url=url_or_path,
                content=content[:5000],  # Store snippet in state
                metadata=metadata,
                trust_score=0.90,  # PDFs are usually high trust
                fetched_at=datetime.now(),
                embedding_index_id=source_id
            )
        except Exception as e:
            logger.error(f"Failed to process PDF {url_or_path}: {e}")
            return RawSource(
                id=f"pdf-error-{hash(url_or_path)}",
                source_type=SourceType.PDF,
                url=url_or_path,
                content="",
                metadata={"error": str(e)},
                trust_score=0.0,
                fetched_at=datetime.now()
            )

    async def _index_content(self, source_id: str, content: str):
        """Chunk and index content using FAISS"""
        chunks = self.text_splitter.split_text(content)
        vectors = self.embedder.embed_documents(chunks)
        
        dim = self.embedder.get_dimension()
        index = faiss.IndexFlatIP(dim)
        index.add(np.array(vectors).astype('float32'))
        
        self.indices[source_id] = index
        self.chunk_store[source_id] = chunks

    def query_index(self, source_id: str, query: str, k: int = 5) -> List[str]:
        """Perform similarity search on a specific indexed PDF"""
        if source_id not in self.indices:
            return []
        
        query_vec = self.embedder.embed_query(query)
        index = self.indices[source_id]
        
        D, I = index.search(np.array([query_vec]).astype('float32'), k)
        
        results = []
        for idx in I[0]:
            if idx != -1 and idx < len(self.chunk_store[source_id]):
                results.append(self.chunk_store[source_id][idx])
        
        return results
