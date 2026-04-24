from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime
from typing import Optional


class UserRegisterRequest(BaseModel):
    email: str
    password: str
    tier: Optional[str] = "free"
    roles: Optional[list[str]] = None


class UserResponse(BaseModel):
    id: UUID
    email: str
    tier: str
    is_active: bool
    roles: list[str] = Field(default=[], validation_alias="role_names")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
