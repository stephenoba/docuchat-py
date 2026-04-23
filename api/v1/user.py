from typing import Annotated

from fastapi import APIRouter, Depends, status

from auth import get_current_user
from schemas import BaseResponse
from schemas.auth import UserResponse

user_router = APIRouter()

@user_router.get("/me", response_model=BaseResponse[UserResponse])
async def get_me(user: Annotated[UserResponse, Depends(get_current_user)]):
    return BaseResponse[UserResponse](
        status="success",
        status_code=status.HTTP_200_OK,
        message="User fetched successfully",
        data=user,
    )