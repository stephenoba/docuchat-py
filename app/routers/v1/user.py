from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.schemas import SuccessResponse
from app.schemas.auth import UserResponse
from app.dependencies.rate_limiter import general_limiter


user_router = APIRouter(dependencies=[Depends(general_limiter)])



@user_router.get("/me", response_model=SuccessResponse[UserResponse])
async def get_me(user: Annotated[UserResponse, Depends(get_current_user)]):
    return SuccessResponse[UserResponse](
        data=user,
        message="User fetched successfully",
    )
