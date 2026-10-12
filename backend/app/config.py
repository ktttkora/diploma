"""
Application configuration module.

Loads settings from environment variables and .env file.
Validates all required configuration parameters.
"""

from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Anthropic API
    ANTHROPIC_API_KEY: str
    CLAUDE_MODEL: str = ""
    AI_ENABLED: bool = True

    # File Storage
    UPLOAD_FOLDER: str = "data/uploads"
    TEMP_FOLDER: str = "data/temp"
    SCREENSHOTS_FOLDER: str = "data/screenshots"
    MAX_UPLOAD_SIZE: int = 1073741824  # 1GB
    MAX_VIDEO_DURATION: int = 600  # 10 minutes
    TEMP_UPLOAD_TTL_HOURS: int = 24

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from JSON string or list."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v):
        """Validate SECRET_KEY is not default placeholder."""
        if "your-super-secret-key" in v or len(v) < 32:
            raise ValueError(
                "SECRET_KEY must be changed from default and be at least 32 characters"
            )
        return v

    @field_validator("ANTHROPIC_API_KEY")
    @classmethod
    def validate_anthropic_key(cls, v):
        """Validate ANTHROPIC_API_KEY format."""
        if not v.startswith("sk-ant-"):
            raise ValueError(
                "ANTHROPIC_API_KEY must start with 'sk-ant-'"
            )
        return v


# Singleton instance
settings = Settings()
