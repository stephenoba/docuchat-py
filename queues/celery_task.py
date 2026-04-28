from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.orm import sessionmaker

from celery import Celery
from config import get_settings
from dbmanager import sync_engine
from models import Document, DocumentStatus, Chunk
from utils import split_document
from logger import task_logger as logger
# from fastapi_events.dispatcher import dispatch
# from config import DOCUMENT_EVENTS

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine, expire_on_commit=False)
settings = get_settings()

app = Celery(
    "docuchat-py",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)


@app.task(
    name="process_document",
    bind=True,
    autoretry_for=(ValueError, Exception),
    retry_kwargs={
        "max_retries": 3,
        "countdown": 1,
    },
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
)
def process_document(self, document_id: str, user_id: str):
    document_id = UUID(document_id)
    user_id = UUID(user_id)

    with SessionLocal() as session:
        document = session.get(Document, document_id)
        if not document:
            raise ValueError(f"Document with id {document_id} not found")
        
        logger.info(f"Starting processing for Document {document_id}")
        
        try:
            document.status = DocumentStatus.PROCESSING.value
            session.add(document)
            session.commit()
            
            # Fetch content while session is active (expire_on_commit=False helps here too)
            content = document.content
            
            logger.info(f"Splitting Document {document_id}")
            self.update_state(state="PROGRESS", meta={"current": 10, "total": 100, "status": "Splitting document"})

            chunks = split_document(content, chunk_size=500, chunk_overlap=100)
            chunk_length = len(chunks)
            
            self.update_state(state="PROGRESS", meta={"current": 40, "total": 100, "status": "Storing chunks"})
            logger.info(f"Storing {chunk_length} chunks for Document {document_id}")
        
            # Use a transaction for chunk operations and document update
            session.execute(delete(Chunk).where(Chunk.document_id == document_id))
            
            new_chunks = [Chunk(document_id=document_id, content=chunk, index=index) for index, chunk in enumerate(chunks)]
            session.add_all(new_chunks)

            document.status = DocumentStatus.READY.value
            document.chunk_count = chunk_length
            session.add(document)
            session.commit()
            
            self.update_state(state="PROGRESS", meta={"current": 100, "total": 100, "status": "Completed"})
            logger.info(f"Successfully processed Document {document_id}")
            # TODO: Figure out a way to pass context here for dispatching events
            # dispatch(DOCUMENT_EVENTS.PROCESSED, payload={"user_id": user_id, "document_id": document_id, "chunk_count": chunk_length})
            return {"success": True, "chunk_length": chunk_length}
            
        except Exception as e:
            session.rollback()
            if self.request.retries >= self.max_retries:
                document.status = DocumentStatus.FAILED.value
                document.error = str(e)
                session.add(document)
                session.commit()
            logger.error(f"Failed to process Document {document_id}: {str(e)}")
            raise Exception(str(e))
        