import logging

from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent

# class RedisSettings(BaseModel):
#     host: str = "localhost"
#     port: int = 6379
#     password: str = ""

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / '.env',
        env_file_encoding='utf-8'
    )
    
    SECRET_KEY: str
    REFRESH_SECRET_KEY: str
    DATABASE_URL: str
    DEBUG: bool
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 1 Day
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7 # 7 Days
    # REDIS: RedisSettings


@lru_cache
def get_settings() -> Settings:
    return Settings()