from pydantic_settings import BaseSettings
from typing import Optional
import os
import secrets
from pydantic import model_validator

DEVELOPMENT_SECRET = secrets.token_urlsafe(48)

class Settings(BaseSettings):
    PROJECT_NAME: str = "ReconOS AI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", DEVELOPMENT_SECRET)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Database
    # Defaults to SQLite locally for immediate out-of-the-box zero-dependency running
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./reconos_ai.db")
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]
    
    # AI Engine Configuration
    AI_ANOMALY_CONTAMINATION: float = 0.05
    TOLERANCE_DEFAULT_DAYS: int = 2
    TOLERANCE_DEFAULT_AMOUNT_PERCENT: float = 0.00  # 0.00% exact amount by default

    @model_validator(mode="after")
    def validate_production_settings(self):
        if self.ENVIRONMENT.lower() == "production":
            if (
                self.SECRET_KEY == DEVELOPMENT_SECRET
                or self.SECRET_KEY.startswith("replace-with-")
                or len(self.SECRET_KEY) < 32
            ):
                raise ValueError("Production requires a unique SECRET_KEY of at least 32 characters")
            if not self.DATABASE_URL.startswith(("postgresql://", "postgresql+")):
                raise ValueError("Production requires PostgreSQL")
            if "*" in self.CORS_ORIGINS:
                raise ValueError("Production CORS origins cannot include a wildcard")
        return self

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
