from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
from functools import lru_cache


class Settings(BaseSettings):
    """Extended application settings"""
    
    # ============================================
    # Existing Settings (from Phase 1 & 2)
    # ============================================
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
    
    # ============================================
    # NEW: FastAPI Settings
    # ============================================
    APP_NAME: str = "Juvo Service Orchestrator API"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    RELOAD: bool = True
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # ============================================
    # NEW: Security Settings
    # ============================================
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # Password
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_BCRYPT_ROUNDS: int = 12
    
    # ============================================
    # NEW: HTL Settings
    # ============================================
    HTL_RESERVATION_MINUTES: int = 5  # Hold time before expiry
    HTL_CLEANUP_INTERVAL_SECONDS: int = 60  # How often to clean expired
    
    # ============================================
    # NEW: Rate Limiting
    # ============================================
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_BURST: int = 10
    
    # ============================================
    # NEW: Redis (for caching & sessions)
    # ============================================
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    
    # ============================================
    # NEW: Notification Settings
    # ============================================
    ENABLE_NOTIFICATIONS: bool = True
    NOTIFICATION_BATCH_SIZE: int = 100
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    @property
    def redis_url(self) -> str:
        """Redis connection URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()