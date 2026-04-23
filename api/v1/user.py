from typing import Annotated

from fastapi import APIRouter, Depends

from auth import get_current_user
from schemas import SuccessResponse
from schemas.auth import UserResponse

user_router = APIRouter()


@user_router.get("/me", response_model=SuccessResponse[UserResponse])
async def get_me(user: Annotated[UserResponse, Depends(get_current_user)]):
    return SuccessResponse[UserResponse](
        data=user,
        message="User fetched successfully",
    )
