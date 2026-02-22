import hashlib
import logging
from fastapi import Request, HTTPException, Security
from fastapi.security import APIKeyHeader
from nexus_insight.config import settings

logger = logging.getLogger(__name__)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def validate_api_key(api_key: str = Security(api_key_header)):
    if not settings.API_KEY_HASH:
        # If no hash is configured, allow all (not recommended for prod)
        return
        
    if not api_key:
        raise HTTPException(status_code=401, detail="X-API-Key header missing")
        
    hashed_key = hashlib.sha256(api_key.encode()).hexdigest()
    if hashed_key != settings.API_KEY_HASH:
        logger.warning(f"Invalid API key attempt: {hashed_key}")
        raise HTTPException(status_code=401, detail="Invalid API Key")
