from fastapi import APIRouter, Depends, HTTPException, status

from auth.auth import register_user
from auth.auth_errors import UserAlreadyExistsError
from schemas import BaseResponse
from schemas.auth import UserRegisterRequest, UserResponse

auth_router = APIRouter()

@auth_router.post("/register", response_model=BaseResponse[UserResponse], status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegisterRequest):
    try:
        user = await register_user(
            email=user_data.email,
            password=user_data.password,
            tier=user_data.tier
        )
        return BaseResponse[UserResponse](
            status="success",
            status_code=status.HTTP_201_CREATED,
            message="User registered successfully",
            data=user
        )
    except UserAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )

@auth_router.post("/token")
async def token():
    pass

@auth_router.post("/refresh")
async def refresh():
    pass

