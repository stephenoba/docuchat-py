import uuid
import logging
from typing import Annotated
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from config import get_settings
from models import User, RefreshToken, Role, UserRole
from schemas.auth import TokenResponse
from dbmanager import async_session
from auth.auth_errors import (
    UserNotFoundError,
    UserAlreadyExistsError,
    InactiveUserError,
    InvalidPasswordError,
    InvalidTokenError,
)

settings = get_settings()
logger = logging.getLogger(__name__)

oauth2_password_bearer = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")
password_hash = PasswordHash.recommended()


def create_password_hash(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


async def get_user(**kwargs) -> User:
    # QueryManager.get can use any field to query the database. So this function can also accept the user_id or email strings.
    print(kwargs)
    return await User.objects.get(**kwargs)


async def register_user(
    email: str, 
    password: str, 
    tier: str = "free", 
    roles: list[str] | None = None,
    assigned_by: uuid.UUID | None = None
) -> User:
    # since the username field is populated with the user's email and the username feild is indexed, we can use the email to check for existing users and it will be faster than querying the email field
    user = await User.objects.get(username=email)
    if user:
        raise UserAlreadyExistsError()
    # TODO: Create test for password strenght and conformity to standards
    password_hash_str = create_password_hash(password)
    
    async with async_session() as session:
        async with session.begin():
            # Create the user
            user = await User.objects.create(
                session=session,
                email=email, 
                password_hash=password_hash_str, 
                tier=tier
            )
            
            # Determine roles to assign
            roles_to_assign = []
            if roles:
                for role_name in roles:
                    role = await Role.objects.get(session=session, name=role_name)
                    if role:
                        roles_to_assign.append(role)
            else:
                # Assign default role if no roles specified
                default_role = await Role.objects.get(session=session, is_default=True)
                if default_role:
                    roles_to_assign.append(default_role)
            
            # Assign roles
            for role in roles_to_assign:
                await UserRole.objects.create(
                    session=session,
                    user_id=user.id,
                    role_id=role.id,
                    assigned_by=assigned_by
                )
    
    return user


async def authenticate_user(username: str, password: str) -> bool:
    user = await get_user(username=username)
    if not user:
        raise UserNotFoundError()
    if not user.is_active:
        raise InactiveUserError()
    if not verify_password(password, user.password_hash):
        raise InvalidPasswordError()
    return await create_tokens(user)


async def logout_user(token: str) -> bool:
    refresh_token = await RefreshToken.objects.get(token=token)
    if not refresh_token:
        raise InvalidTokenError("Invalid refresh token")
    if refresh_token.is_revoked:
        raise InvalidTokenError("Refresh token is revoked")
    if refresh_token.is_used:
        raise InvalidTokenError("Refresh token is used")
    if refresh_token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(
        timezone.utc
    ):
        raise InvalidTokenError("Refresh token is expired")
    refresh_token.is_revoked = True
    await RefreshToken.objects.save(refresh_token)
    return True


def create_access_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "tier": user.tier,
        "exp": datetime.now(timezone.utc)
        + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def create_refresh_token(user: User) -> str:
    expired_at = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {
        "sub": str(user.id),
        "tier": user.tier,
        "exp": expired_at,
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid.uuid4()),
        "type": "refresh",
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    await RefreshToken.objects.create(
        user_id=user.id,
        token=token,
        expires_at=expired_at,
    )
    return token


async def create_tokens(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user),
        refresh_token=await create_refresh_token(user),
        token_type="Bearer",
    )


def verify_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        if payload["type"] != "access":
            raise InvalidTokenError("Invalid token type")
        return payload
    except jwt.ExpiredSignatureError:
        raise InvalidTokenError("Token expired")
    except jwt.InvalidTokenError:
        raise InvalidTokenError("Invalid token")


def verify_refresh_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token, settings.REFRESH_SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        if payload["type"] != "refresh":
            raise ValueError("Invalid token type")
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")


async def refresh_access_token(refresh_token_str: str) -> TokenResponse:
    try:
        refresh_token = await RefreshToken.objects.get(token=refresh_token_str)
        if not refresh_token:
            raise InvalidTokenError("Invalid refresh token")
        if refresh_token.is_revoked:
            raise InvalidTokenError("Refresh token is revoked")
        if refresh_token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(
            timezone.utc
        ):
            raise InvalidTokenError("Refresh token is expired")
        if refresh_token.is_used:
            raise InvalidTokenError("Refresh token is used")
        refresh_token.is_used = True
        await RefreshToken.objects.save(refresh_token)
        user = await User.objects.get_by_id(refresh_token.user_id)
        if not user:
            raise InvalidTokenError("User not found")

        return await create_tokens(user)
    except ValueError as e:
        raise ValueError(e)


async def get_current_user(token: Annotated[str, Depends(oauth2_password_bearer)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = verify_access_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except InvalidTokenError as e:
        logger.error(e)
        raise credentials_exception
    try:
        user_uuid = uuid.UUID(user_id)
    except (ValueError, AttributeError):
        raise credentials_exception

    user = await get_user(id=user_uuid)
    if user is None:
        raise credentials_exception
    return user
