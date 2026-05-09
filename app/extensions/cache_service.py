import json
from typing import Any, TypeVar, Optional, Callable

from app.extensions.redis import redis_client as cache_redis


T = TypeVar("T")

# Constants for TTL
DEFAULT = "default"
PERMISSIONS = "permissions"
DOCUMENT = "document"
CONVERSATION_LIST = "conversation_list"
EMBEDDING = "embedding"
RAG_RESULT = "rag_result"

CACHE_TTL = {
    DEFAULT: 3600,
    PERMISSIONS: 300,        # 5 minutes
    DOCUMENT: 600,           # 10 minutes
    CONVERSATION_LIST: 120,  # 2 minutes
    EMBEDDING: 604800,       # 7 days
    RAG_RESULT: 3600,        # 1 hour
}
CACHE_PREFIX = "docuchat:"

def _get_prefixed_key(key: str) -> str:
    """Prepend the global prefix to a key."""
    return f"{CACHE_PREFIX}{key}"

async def cache_has(key: str) -> bool:
    """Check if a key exists in cache."""
    prefixed_key = _get_prefixed_key(key)
    return await cache_redis.exists(prefixed_key)

async def cache_get_ttl(key: str) -> int:
    """Get the TTL of a key."""
    prefixed_key = _get_prefixed_key(key)
    return await cache_redis.ttl(prefixed_key)

async def cache_get(key: str) -> Optional[T]:
    """Get a value from cache and parse it as JSON."""
    prefixed_key = _get_prefixed_key(key)
    raw = await cache_redis.get(prefixed_key)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None

async def cache_set(key: str, value: Any, ttl_seconds: int) -> None:
    """Set a value in cache as JSON with a TTL."""
    prefixed_key = _get_prefixed_key(key)
    await cache_redis.set(prefixed_key, json.dumps(value), ex=ttl_seconds)

async def cache_remember(key: str, func: Callable, *args, ttl_seconds: int = None) -> T:
    """Get a value from cache or set it if not found."""
    lock_key = f"{key}:lock"
    lock = await cache_redis.setnx(lock_key, 1, ex=60)
    if lock:
        try:
            if await cache_has(key):
                return await cache_get(key)
            value = await func(*args)
            await cache_set(key, value, ttl_seconds or CACHE_TTL[DEFAULT])
        finally:
            await cache_redis.delete(lock_key)
    else:
        # wait for the lock to be released
        await cache_get(key)
    return await cache_get(key)

async def cache_update(key: str, value: Any, ttl_seconds: int = None) -> None:
    """Update a value in cache."""
    if await cache_has(key):
        if ttl_seconds:
            await cache_set(key, value, ttl_seconds)
        else:
            current_ttl = await cache_get_ttl(key)
            await cache_set(key, value, current_ttl)
        return
    await cache_set(key, value, ttl_seconds or CACHE_TTL[DEFAULT])

async def cache_del(key: str) -> None:
    """Delete a key from cache."""
    prefixed_key = _get_prefixed_key(key)
    await cache_redis.delete(prefixed_key)

async def cache_del_pattern(pattern: str) -> None:
    """
    Delete all keys matching a pattern.
    Uses SCAN instead of KEYS to avoid blocking the Redis server.
    """
    prefixed_pattern = _get_prefixed_key(pattern)
    async with cache_redis.pipeline(transaction=True) as pipe:
        async for key in cache_redis.scan_iter(match=prefixed_pattern, count=100):
            pipe.delete(key)
        await pipe.execute()

async def cache_clear():
    """Clear the cache."""
    await cache_redis.flushdb()
