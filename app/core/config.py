from enum import Enum
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


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


class AI_EVENTS(Enum):
    EMBEDDING_GENERATED = "ai:embedding-generated"
    CHAT_COMPLETED = "ai:chat-completed"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env", env_file_encoding="utf-8"
    )

    SECRET_KEY: str
    REFRESH_SECRET_KEY: str
    DATABASE_URL: str
    REDIS_URL: str
    REDIS_HOST: str
    REDIS_PORT: int
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

    # OpenAI Settings (Ollama compatible)
    USE_OLLAMA: bool = True
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536 # OpenAI Text Embedding v3 small
    OPENAI_RETRY_DELAY: int = 1
    WEBHOOK_SECRET: str = ""
    CORS_ORIGINS: list[str] = ["*"]



@lru_cache
def get_settings() -> Settings:
    return Settings()
