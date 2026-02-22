import os
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # LLM (Free Groq + Local Ollama)
    GROQ_API_KEY: str = ""           # Get free at console.groq.com
    GROQ_FAST_MODEL: str = "llama-3.1-8b-instant"
    GROQ_REASONING_MODEL: str = "llama-3.3-70b-versatile"
    
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_FAST_MODEL: str = "qwen2.5:7b"
    OLLAMA_REASONING_MODEL: str = "qwen2.5:72b"
    
    LLM_MODE: Literal["groq", "ollama", "auto"] = "auto"
    
    # Embeddings (local, no key needed)
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    EMBEDDING_FALLBACK: str = "all-MiniLM-L6-v2"
    
    # Web Search (free)
    SEARXNG_URL: str = "http://searxng:8888"
    DDG_RATE_LIMIT_DELAY: float = 1.1
    
    # Media (local)
    WHISPER_MODEL: Literal["tiny", "base", "small", "medium", "large-v3"] = "base"
    
    # Infrastructure (free/self-hosted)
    REDIS_URL: str = "redis://localhost:6379"
    OTEL_EXPORTER_ENDPOINT: str = "http://otel-collector:4317"
    
    # Agent Behavior
    MAX_REVISION_COUNT: int = 5
    TOKEN_BUDGET: int = 200_000
    CONFIDENCE_THRESHOLD: float = 0.85
    FAITHFULNESS_THRESHOLD: float = 0.80
    
    # API Auth (local key)
    API_KEY_HASH: str = ""
    
    # App
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: Literal["development", "production"] = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    
    # Timeouts
    TIMEOUT_PDF: int = 30
    TIMEOUT_WEB: int = 15
    TIMEOUT_VIDEO: int = 120
    TIMEOUT_LLM: int = 60

settings = Settings()
