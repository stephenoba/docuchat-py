import hashlib
import redis.asyncio as redis

from app.core.config import get_settings

settings = get_settings()

redis_client = redis.Redis(
    host=settings.REDIS_HOST, 
    port=settings.REDIS_PORT, 
    decode_responses=True
)

def hash_key(*parts: str) -> str:
    """
    Generate a short deterministic hash for a key based on its parts.
    Returns the first 16 characters of the SHA-256 hash.
    """
    data = ":".join(parts)
    return hashlib.sha256(data.encode()).hexdigest()[:16]