import logging
from enum import Enum
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent


class AUTH_EVENTS(Enum):
    USER_REGISTERED = "auth:user-registered"
    USER_LOGGED_IN = "auth:user-logged-in"
    USER_LOGGED_OUT = "auth:user-logged-out"
    TOKEN_REFRESHED = "auth:token-refreshed"
    LOGIN_FAILED = "auth:login-failed"


class ADMIN_EVENTS(Enum):
    ROLE_ASSIGNED = "admin:role-assigned"
    ROLE_REVOKED = "admin:role-revoked"


class DOCUMENT_EVENTS(Enum):
    CREATED = "doc:created"
    PROCESSED = "doc:processed"
    DELETED = "doc:deleted"
    RESTORED = "doc:restored"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env", env_file_encoding="utf-8"
    )

    SECRET_KEY: str
    REFRESH_SECRET_KEY: str
    DATABASE_URL: str
    REDIS_URL: str
    DEBUG: bool
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 Day
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # 7 Days

    # Celery Settings
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None

    # Document Processing Settings
    DOC_PROCESSING_CHUNK_SIZE: int = 500
    DOC_PROCESSING_CHUNK_OVERLAP: int = 100
    DOC_PROCESSING_MAX_RETRIES: int = 3
    DOC_PROCESSING_RETRY_BACKOFF: bool = True

    # OpenAI Settings
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_RETRY_DELAY: int = 1
    WEBHOOK_SECRET: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
