from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from pwdlib import PasswordHash

from config import get_settings
from models import User, RefreshToken
from auth.auth_errors import UserNotFoundError, InactiveUserError, InvalidPasswordError

settings = get_settings()

password_hash = PasswordHash.recommended()

def create_password_hash(password: str) -> str:
    return password_hash.hash(password)

def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)

def get_user(username: str) -> User:
    return User.objects.get(username=username)

def authenticate_user(username: str, password: str) -> bool:
    user = get_user(username)
    if not user:
        raise UserNotFoundError()
    if not user.is_active:
        raise InactiveUserError()
    if not verify_password(password, user.password_hash):
        raise InvalidPasswordError()
    return create_tokens(user)

def create_access_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "tier": user.tier,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "type": "access"
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "tier": user.tier,
        "exp": datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        "type": "refresh"
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    RefreshToken.objects.create(
        user_id=user.id,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    return token

def create_tokens(user: User,) -> dict:
    return {
        "access_token": create_access_token(user),
        "refresh_token": create_refresh_token(user),
    }

def verify_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload["type"] != "access":
            raise ValueError("Invalid token type")
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")

def verify_refresh_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.REFRESH_SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload["type"] != "refresh":
            raise ValueError("Invalid token type")
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")

def refresh_access_token(self, refresh_token: str) -> str:
    try:
        refresh_token = RefreshToken.objects.get(token=refresh_token)
        if not refresh_token:
            raise ValueError("Invalid refresh token")
        if refresh_token.is_revoked:
            raise ValueError("Refresh token is revoked")
        if refresh_token.expires_at < datetime.now(timezone.utc):
            raise ValueError("Refresh token is expired")
        if refresh_token.is_used:
            raise ValueError("Refresh token is used")
        refresh_token.is_used = True
        refresh_token.save()
        user = refresh_token.user
        return self.create_token(user)
    except ValueError as e:
        raise ValueError(e)
