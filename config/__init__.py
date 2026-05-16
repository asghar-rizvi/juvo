from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):    
    DATABASE_URL: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    
    GOOGLE_CLOUD_PROJECT: str
    GOOGLE_APPLICATION_CREDENTIALS: str
    VERTEX_AI_LOCATION: str = "us-central1"
    
    GEMINI_API_KEY: str
    GOOGLE_MAPS_API_KEY: str
    
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    TIMEZONE: str = "Asia/Karachi"
    
    SECRET_KEY: str
    
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    @property
    def database_url_sync(self) -> str:
        return self.DATABASE_URL
    
    @property
    def database_url_async(self) -> str:
        return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()