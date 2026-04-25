from typing import Annotated, List
import uuid
import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_events.dispatcher import dispatch
from sqlmodel import select, func
from sqlalchemy.orm import selectinload

from auth import PermissionChecker
from models import User, Role, UserRole, RolePermission, UsageLog
from schemas import SuccessResponse
from schemas.admin import RoleResponse, RoleAssignmentRequest
from dbmanager import async_session
from config import ADMIN_EVENTS

admin_router = APIRouter()

@admin_router.get("/roles", response_model=SuccessResponse[List[RoleResponse]])
async def list_roles(
    admin: Annotated[User, Depends(PermissionChecker("roles:manage"))]
):
    async with async_session() as session:
        # Get roles with permissions and member counts
        statement = (
            select(Role)
            .options(
                selectinload(Role.permissions).selectinload(RolePermission.permission)
            )
        )
        results = await session.execute(statement)
        roles = results.scalars().all()
        
        response_data = []
        for role in roles:
            # Count users for this role
            count_stmt = select(func.count(UserRole.id)).where(UserRole.role_id == role.id)
            count_result = await session.execute(count_stmt)
            user_count = count_result.scalar() or 0
            
            # Extract permissions
            role_perms = [rp.permission for rp in role.permissions if rp.permission]
            
            response_data.append(RoleResponse(
                id=role.id,
                name=role.name,
                description=role.description,
                is_default=role.is_default,
                permissions=role_perms,
                user_count=user_count
            ))
            
    return SuccessResponse[List[RoleResponse]](
        data=response_data,
        message="Roles retrieved successfully"
    )

@admin_router.post("/users/{user_id}/roles", response_model=SuccessResponse)
async def assign_role(
    admin: Annotated[User, Depends(PermissionChecker("roles:manage"))],
    user_id: uuid.UUID,
    data: RoleAssignmentRequest
):
    async with async_session() as session:
        # Check if user exists
        user = await User.objects.get(session=session, id=user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
        # Check if role exists
        role = await Role.objects.get(session=session, name=data.role_name)
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        
        # Check if already assigned
        existing = await UserRole.objects.get(session=session, user_id=user_id, role_id=role.id)
        if existing:
            return SuccessResponse(message=f"Role '{data.role_name}' already assigned to user")
        
        # Assign role
        await UserRole.objects.create(
            session=session,
            user_id=user_id,
            role_id=role.id,
            assigned_by=admin.id,
            is_default=False # Manual assignment usually isn't the primary default unless specified
        )
        
        await session.commit()
        
    # Log and dispatch
    metadata = {"target_user_id": str(user_id), "role_name": data.role_name}
    dispatch(ADMIN_EVENTS.ROLE_ASSIGNED, payload={"admin_id": admin.id, **metadata})
    
    return SuccessResponse(message=f"Role '{data.role_name}' assigned to user successfully")

@admin_router.delete("/users/{user_id}/roles/{role_name}", response_model=SuccessResponse)
async def revoke_role(
    admin: Annotated[User, Depends(PermissionChecker("roles:manage"))],
    user_id: uuid.UUID,
    role_name: str
):
    async with async_session() as session:
        # Check if role exists
        role = await Role.objects.get(session=session, name=role_name)
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
            
        # Check if assignment exists
        user_role = await UserRole.objects.get(session=session, user_id=user_id, role_id=role.id)
        if not user_role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role assignment not found")
        
        # Delete assignment
        await session.delete(user_role)
        await session.commit()
        
    # Log and dispatch
    metadata = {"target_user_id": str(user_id), "role_name": role_name}
    dispatch(ADMIN_EVENTS.ROLE_REVOKED, payload={"admin_id": admin.id, **metadata})
    
    return SuccessResponse(message=f"Role '{role_name}' revoked from user successfully")
