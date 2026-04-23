from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional


class UserRegisterRequest(BaseModel):
    email: str
    password: str
    tier: Optional[str] = "free"


class UserResponse(BaseModel):
    id: UUID
    email: str
    tier: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
