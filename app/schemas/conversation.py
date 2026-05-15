from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.document import Citation


class ConversationCreate(BaseModel):
    title: str


class ConversationUpdate(BaseModel):
    title: Optional[str] = None


class ConversationResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageCreate(BaseModel):
    content: str
    document_id: Optional[UUID] = None


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    document_id: Optional[UUID] = None
    role: str
    content: str
    sources: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenUsage(BaseModel):
    prompt: int
    completion: int
    total: int


class RAGResponse(BaseModel):
    answer: str
    citations: list[Citation]
    tokens_used: TokenUsage
    cost_usd: float
    model: str
