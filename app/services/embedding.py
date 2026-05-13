import hashlib
import math
from typing import List, Optional

from fastapi_events.dispatcher import dispatch
from sqlalchemy import text

from app.core.config import AI_EVENTS, get_settings
from app.core.logger import client_logger as logger
from app.extensions.cache_service import CACHE_TTL, EMBEDDING, cache_get, cache_set
from app.models.dbmanager import async_session
from app.services.breaker import openai_request

settings = get_settings()

MODEL = settings.OPENAI_EMBEDDING_MODEL
EMBEDDING_DIMENSION = settings.EMBEDDING_DIMENSION


def content_hash(text: str) -> str:
    """SHA-256 hash of text for cache keys."""
    return hashlib.sha256(text.encode()).hexdigest()


async def generate_embeddings(
    texts: List[str], user_id: Optional[str] = None, document_id: Optional[str] = None
) -> List[List[float]]:
    """
    Generates embeddings for a list of texts using the configured AI service.
    Dispatches an event with token usage and cost metadata.
    """
    if not texts:
        return []

    BATCH_SIZE = 100
    all_embeddings = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch_texts = texts[i : i + BATCH_SIZE]
        try:
            response = await openai_request(
                method="POST",
                path="/embeddings",
                body={
                    "model": MODEL,
                    "input": batch_texts,
                    "encoding_format": "float",
                },
            )

            data = response.json()
            sorted_embeddings = sorted(data.get("data", []), key=lambda x: x["index"])
            embeddings = [emb["embedding"] for emb in sorted_embeddings]
            all_embeddings.extend(embeddings)

            usage = data.get("usage", {})
            tokens_used = usage.get("total_tokens", 0)

            # Emit event for monitoring/billing
            dispatch(
                AI_EVENTS.EMBEDDING_GENERATED,
                payload={
                    "user_id": user_id,
                    "document_id": document_id,
                    "model": MODEL,
                    "tokens_used": tokens_used,
                    "cost_usd": (tokens_used / 1_000_000) * 0.02,
                    "cached": False,
                    "batch_size": len(batch_texts),
                },
            )

            logger.info(
                "Embedding batch processed",
                extra={
                    "batchIndex": math.floor(i / BATCH_SIZE),
                    "batchSize": len(batch_texts),
                    "totalTexts": len(texts),
                    "tokensUsed": tokens_used,
                },
            )
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise

    return all_embeddings


async def generate_embedding_cached(
    text_content: str, user_id: Optional[str] = None, document_id: Optional[str] = None
) -> List[float]:
    """
    Generates an embedding for a single text, checking cache first.
    """
    hash_val = content_hash(text_content)
    cache_key = f"embed:{hash_val}"

    # 1. Check cache
    cached = await cache_get(cache_key)
    if cached:
        logger.debug("Embedding cache hit", extra={"hash": hash_val[:12]})
        return cached

    # 2. Cache miss — generate
    embeddings = await generate_embeddings([text_content], user_id, document_id)
    embedding = embeddings[0]

    # 3. Cache for 7 days (TTL defined in extensions/cache_service.py)
    await cache_set(cache_key, embedding, ttl_seconds=CACHE_TTL[EMBEDDING])
    logger.debug("Embedding cached", extra={"hash": hash_val[:12]})

    return embedding


async def generate_embeddings_batch_cached(
    texts: List[str], user_id: Optional[str] = None, document_id: Optional[str] = None
) -> List[List[float]]:
    """
    Generates embeddings for multiple texts, checking cache for each.
    Only requests missing embeddings from the AI service.
    """
    results: List[Optional[List[float]]] = [None] * len(texts)
    uncached: List[dict] = []

    # 1. Check cache for each text
    for i, t in enumerate(texts):
        hash_val = content_hash(t)
        cached = await cache_get(f"embed:{hash_val}")
        if cached:
            results[i] = cached
        else:
            uncached.append({"index": i, "text": t})

    logger.info(
        "Embedding batch cache check",
        extra={
            "total": len(texts),
            "cacheHits": len(texts) - len(uncached),
            "cacheMisses": len(uncached),
        },
    )

    # 2. Generate embeddings only for uncached texts
    if uncached:
        batch_texts = [u["text"] for u in uncached]
        new_embeddings = await generate_embeddings(batch_texts, user_id, document_id)

        # 3. Cache the new embeddings and fill in results
        for i, emb in enumerate(new_embeddings):
            original_idx = uncached[i]["index"]
            original_text = uncached[i]["text"]
            hash_val = content_hash(original_text)

            await cache_set(cache_key=f"embed:{hash_val}", value=emb, ttl_seconds=CACHE_TTL[EMBEDDING])
            results[original_idx] = emb

    return results  # type: ignore


async def store_chunk_embedding(chunk_id: str, embedding: List[float]) -> None:
    """
    Updates a single chunk with its embedding vector.
    """
    async with async_session() as session:
        await session.execute(
            text("UPDATE chunk SET embedding = :embedding WHERE id = :id"),
            {"embedding": str(embedding), "id": chunk_id},
        )
        await session.commit()


async def store_chunk_embeddings_batch(chunks: List[dict]) -> None:
    """
    Updates multiple chunks in a single transaction for atomicity.
    chunks: List of dictionaries with 'id' and 'embedding' keys.
    """
    async with async_session() as session:
        async with session.begin():
            for chunk in chunks:
                await session.execute(
                    text("UPDATE chunk SET embedding = :embedding WHERE id = :id"),
                    {"embedding": str(chunk["embedding"]), "id": chunk["id"]},
                )
