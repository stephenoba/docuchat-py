from uuid import UUID
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

class PermissionSimple(BaseModel):
    name: str
    resource: str
    action: str
    
    model_config = ConfigDict(from_attributes=True)

class RoleResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    is_default: bool
    permissions: List[PermissionSimple] = []
    user_count: int = 0
    
    model_config = ConfigDict(from_attributes=True)

class RoleAssignmentRequest(BaseModel):
    role_name: str
