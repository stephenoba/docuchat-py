from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentUpdate(BaseModel):
    title: Optional[str] = None


class DocumentStatusUpdate(BaseModel):
    status: str
    task_id: Optional[str] = None
    error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    filename: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[UUID] = None
    task_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SearchResult(BaseModel):
    chunk_id: UUID
    document_id: UUID
    document_title: str
    content: str
    chunk_index: int
    score: float
    token_count: int


class Citation(BaseModel):
    index: int
    chunk_id: UUID
    document_id: UUID
    document_title: str
    chunk_index: int
    score: float


class AssembledContext(BaseModel):
    chunks: list[SearchResult]
    context_text: str
    total_tokens: int
    citations: list[Citation]
