from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):   
    #local 
    # DATABASE_URL: str
    
    
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_DB: Optional[str] = None
    POSTGRES_HOST: Optional[str] = "localhost"
    POSTGRES_PORT: Optional[int] = 5432
    # deployment
    DATABASE_URL : str
    DATABASE_URL_SYNC : str
    
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
    
    HTL_RESERVATION_MINUTES : int = 5
    HTL_CLEANUP_INTERVAL_SECONDS : int =60
    
    ENABLE_NOTIFICATIONS: bool = True  
    NOTIFICATION_BATCH_SIZE: int = 100

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