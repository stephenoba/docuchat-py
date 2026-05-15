import time
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.orm import sessionmaker
from celery import Celery

from app.core.config import get_settings, DOCUMENT_EVENTS
from app.models.dbmanager import sync_engine
from app.models.models import Document, DocumentStatus, Chunk
from app.core.utils import detect_format, extract_text, split_document
from app.core.logger import task_logger as logger
from app.services.embedding import (
    generate_embeddings_batch_cached_sync,
    store_chunk_embeddings_batch_sync
)
from app.core.utils import safe_dispatch
from app.core.metrics import DOCUMENTS_PROCESSED, ACTIVE_QUEUE_JOBS

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine, expire_on_commit=False)
settings = get_settings()

app = Celery(
    "docuchat-py",
    broker=settings.CELERY_BROKER_URL or settings.REDIS_URL,
    backend=settings.CELERY_RESULT_BACKEND or settings.REDIS_URL,
)


@app.task(
    name="process_document",
    bind=True,
    autoretry_for=(ValueError, Exception),
    retry_kwargs={
        "max_retries": settings.DOC_PROCESSING_MAX_RETRIES,
        "countdown": 1,
    },
    retry_backoff=settings.DOC_PROCESSING_RETRY_BACKOFF,
    retry_backoff_max=60,
    retry_jitter=True,
)
def process_document(self, document_id: str, user_id: str, correlation_id: str):
    ACTIVE_QUEUE_JOBS.labels(queue='default').inc()
    try:
        return self._process_document_impl(document_id, user_id, correlation_id)
    finally:
        ACTIVE_QUEUE_JOBS.labels(queue='default').dec()


def _process_document_impl(self, document_id: str, user_id: str, correlation_id: str):
    start_time = time.time()
    document_id = UUID(document_id)
    user_id = UUID(user_id)
    correlation_id = UUID(correlation_id)

    with SessionLocal() as session:
        # Step 1: Mark as processing
        document = session.get(Document, document_id)
        if not document:
            logger.error(f"[{correlation_id}] Document {document_id} not found")
            return {"success": False, "error": "Document not found"}

        logger.info(f"[{correlation_id}] Document processing started", extra={
            "correlationId": str(correlation_id),
            "documentId": str(document_id),
            "userId": str(user_id)
        })

        try:
            document.status = DocumentStatus.PROCESSING.value
            session.add(document)
            session.commit()
            self.update_state(state="PROGRESS", meta={"current": 5, "total": 100, "status": "Processing"})

            # Extract text
            format = detect_format(document.filename)
            extraction = extract_text(document.content, format)
            text = extraction['text']
            page_count = extraction['page_count']
            self.update_state(state="PROGRESS", meta={"current": 15, "total": 100, "status": "Text extracted"})

            logger.info(f"[{correlation_id}] Text extracted", extra={
                "correlationId": str(correlation_id),
                "documentId": str(document_id),
                "format": format,
                "textLength": len(text),
                "pageCount": page_count
            })

            # Chunk the text
            chunks = split_document(
                text,
                chunk_size=settings.DOC_PROCESSING_CHUNK_SIZE,
                chunk_overlap=settings.DOC_PROCESSING_CHUNK_OVERLAP,
                min_chunk_tokens=50,
                model_name=settings.OPENAI_MODEL
            )
            self.update_state(state="PROGRESS", meta={"current": 30, "total": 100, "status": "Document chunked"})

            chunk_count = len(chunks)
            avg_tokens = 0
            if chunk_count > 0:
                avg_tokens = sum(c['token_count'] for c in chunks) // chunk_count

            logger.info(f"[{correlation_id}] Document chunked", extra={
                "correlationId": str(correlation_id),
                "documentId": str(document_id),
                "chunkCount": chunk_count,
                "avgTokens": avg_tokens
            })

            # Store chunks in database
            session.execute(delete(Chunk).where(Chunk.document_id == document_id))
            
            new_chunks = [
                Chunk(
                    document_id=document_id,
                    index=c['index'],
                    content=c['content'],
                    token_count=c['token_count']
                ) for c in chunks
            ]
            session.add_all(new_chunks)
            session.commit() # Commit to get Chunk IDs
            self.update_state(state="PROGRESS", meta={"current": 50, "total": 100, "status": "Chunks stored"})

            # Generate and Store embeddings (Sync)
            chunk_texts = [c['content'] for c in chunks]
            
            # Fetch stored chunks to get their IDs
            stmt = select(Chunk).where(Chunk.document_id == document_id).order_by(Chunk.index.asc())
            stored_chunks = session.execute(stmt).scalars().all()
            
            embeddings = generate_embeddings_batch_cached_sync(
                chunk_texts,
                user_id=str(user_id),
                document_id=str(document_id)
            )
            
            store_chunk_embeddings_batch_sync([
                {
                    "id": str(c.id),
                    "embedding": embeddings[i]
                } for i, c in enumerate(stored_chunks)
            ])

            self.update_state(state="PROGRESS", meta={"current": 95, "total": 100, "status": "Embeddings processed"})

            # Mark complete
            document.status = DocumentStatus.READY.value
            document.chunk_count = chunk_count
            session.add(document)
            session.commit()
            self.update_state(state="PROGRESS", meta={"current": 100, "total": 100, "status": "Complete"})

            duration_ms = int((time.time() - start_time) * 1000)

            # Emit completion event with metrics
            safe_dispatch(DOCUMENT_EVENTS.PROCESSED.value, payload={
                "document_id": str(document_id),
                "user_id": str(user_id),
                "correlation_id": str(correlation_id),
                "chunk_count": chunk_count,
                "duration_ms": duration_ms,
                "format": format,
                "page_count": page_count,
                "tokens": sum(c['token_count'] for c in chunks)
            })

            logger.info(f"[{correlation_id}] Document processing complete", extra={
                "correlationId": str(correlation_id),
                "documentId": str(document_id),
                "chunkCount": chunk_count,
                "durationMs": duration_ms
            })

            DOCUMENTS_PROCESSED.labels(status='success').inc()
            return {
                "success": True,
                "chunks": chunk_count,
                "durationMs": duration_ms
            }

        except Exception as e:
            session.rollback()
            logger.error(f"[{correlation_id}] Document processing failed", extra={
                "correlationId": str(correlation_id),
                "documentId": str(document_id),
                "error": str(e),
                "attempt": self.request.retries + 1
            })

            if self.request.retries >= self.max_retries:
                document.status = DocumentStatus.FAILED.value
                document.error = str(e)
                session.add(document)
                session.commit()
            
            DOCUMENTS_PROCESSED.labels(status='failed').inc()
            raise e
        