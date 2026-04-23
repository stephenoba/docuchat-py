from fastapi import APIRouter, HTTPException, status
from fastapi_events.dispatcher import dispatch

from auth import register_user, authenticate_user, refresh_access_token, logout_user
from auth.auth_errors import (
    UserAlreadyExistsError,
    UserNotFoundError,
    InvalidPasswordError,
    InactiveUserError,
    InvalidTokenError,
)
from schemas import SuccessResponse
from schemas.auth import UserRegisterRequest, UserResponse, TokenResponse
from config import AUTH_EVENTS

auth_router = APIRouter()


@auth_router.post(
    "/register",
    response_model=SuccessResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
)
async def register(user_data: UserRegisterRequest):
    try:
        user = await register_user(
            email=user_data.email, password=user_data.password, tier=user_data.tier
        )
        dispatch(AUTH_EVENTS.USER_REGISTERED, payload=user)
        return SuccessResponse[UserResponse](
            data=user,
            message="User registered successfully",
        )
    except UserAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="User already exists"
        )


@auth_router.post("/token", response_model=SuccessResponse[TokenResponse])
async def token(email: str, password: str):
    try:
        tokens = await authenticate_user(email, password)
        return SuccessResponse[TokenResponse](
            data=tokens,
            message="User authenticated successfully",
        )
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    except InvalidPasswordError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    except InactiveUserError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive"
        )


@auth_router.post("/refresh", response_model=SuccessResponse[TokenResponse])
async def refresh(token: str):
    try:
        tokens = await refresh_access_token(token)
        return SuccessResponse[TokenResponse](
            data=tokens,
            message="Token refreshed successfully",
        )
    except InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@auth_router.post("/logout", response_model=SuccessResponse)
async def logout(token: str):
    try:
        await logout_user(token)
        return SuccessResponse(
            message="User logged out successfully",
        )
    except InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
