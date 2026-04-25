from uuid import UUID
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


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
