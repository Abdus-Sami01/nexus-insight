from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, HttpUrl, Field
from nexus_insight.cognition.state import ThoughtEntry, RawSource, Citation

class ResearchRequest(BaseModel):
    query: str = Field(..., max_length=2000)
    modalities: List[Literal["pdf", "web", "video"]] = ["web"]
    pdf_urls: Optional[List[HttpUrl]] = None
    video_urls: Optional[List[HttpUrl]] = None
    stream: bool = True
    confidence_threshold: float = 0.85
    llm_mode: Literal["groq", "ollama", "auto"] = "auto"
    whisper_model: str = "base"

class FinalReport(BaseModel):
    session_id: str
    query: str
    report_markdown: str
    confidence_score: float
    faithfulness_score: float
    citations: List[Citation]
    total_tokens: int

class SSEEvent(BaseModel):
    event: Literal["thought", "source", "progress", "result", "error", "heartbeat"]
    data: Any
