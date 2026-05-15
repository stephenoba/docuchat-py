import time
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Document, Chunk, DocumentStatus
from app.services.embedding import generate_embedding_cached
from app.schemas.document import SearchResult
from app.core.logger import client_logger as logger


async def semantic_search(
    query: str,
    user_id: UUID,
    session: AsyncSession,
    document_id: Optional[UUID] = None,
    top_k: int = 10,
    min_score: float = 0.3,
    correlation_id: Optional[str] = None
) -> List[SearchResult]:
    """
    Performs semantic search across chunks using vector similarity.
    """
    start_time = time.perf_counter()

    # Step 1: Embed the query
    query_embedding = await generate_embedding_cached(query, user_id=str(user_id))

    # Step 2: Build search query
    # Using pgvector cosine distance: 1 - distance = similarity
    similarity = (1 - Chunk.embedding.cosine_distance(query_embedding)).label("score")

    stmt = select(
        Chunk.id.label("chunk_id"),
        Chunk.document_id,
        Document.title.label("document_title"),
        Chunk.content,
        Chunk.index.label("chunk_index"),
        Chunk.token_count,
        similarity
    ).join(
        Document, Document.id == Chunk.document_id
    ).where(
        and_(
            Document.user_id == user_id,
            Document.deleted_at.is_(None),
            Document.status == DocumentStatus.READY.value,
            Chunk.embedding.isnot(None)
        )
    )

    if document_id:
        stmt = stmt.where(Document.id == document_id)

    # Sort by similarity and limit
    stmt = stmt.order_by(Chunk.embedding.cosine_distance(query_embedding)).limit(top_k)

    # Execute
    results = (await session.execute(stmt)).all()

    # Step 3: Filter by min_score and map to schema
    # The database query already sorted by similarity, but we filter min_score in Python 
    # for simplicity as 'score' label might not be available in WHERE clause depending on DB
    filtered_results = []
    for r in results:
        if r.score >= min_score:
            filtered_results.append(SearchResult(
                chunk_id=r.chunk_id,
                document_id=r.document_id,
                document_title=r.document_title,
                content=r.content,
                chunk_index=r.chunk_index,
                score=float(r.score),
                token_count=r.token_count
            ))

    duration_ms = int((time.perf_counter() - start_time) * 1000)
    
    logger.info(
        "Semantic search completed",
        extra={
            "query": query[:100],
            "totalResults": len(results),
            "filteredResults": len(filtered_results),
            "topScore": round(filtered_results[0].score, 4) if filtered_results else 0,
            "durationMs": duration_ms,
            "correlationId": correlation_id
        }
    )

    return filtered_results
