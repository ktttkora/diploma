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

    # AI provider: "grok_cli" (Grok subscription), "claude_cli", or "claude"
    AI_PROVIDER: str = "grok_cli"
    AI_ENABLED: bool = True

    # Official Anthropic API. A custom base URL is not supported.
    ANTHROPIC_API_KEY: str = ""
    CLAUDE_MODEL: str = ""

    # Local Grok CLI signed in with `grok login` (subscription, no API key)
    GROK_CLI_PATH: str = "grok"
    GROK_CLI_MODEL: str = ""  # Empty = subscription default model
    GROK_CLI_TIMEOUT: int = 600

    # Local Claude Code CLI (claude.ai subscription, no API key)
    CLAUDE_CLI_PATH: str = "claude"
    CLAUDE_CLI_MODEL: str = ""  # Empty = subscription default model
    CLAUDE_CLI_TIMEOUT: int = 600  # Seconds before the CLI process is killed

    # Reference examples passed to the AI for element recognition
    AI_REFERENCE_EXAMPLES: bool = True
    AI_REFERENCE_CANDIDATES: int = 8
    AI_REFERENCE_FRAMES_PER_ELEMENT: int = 2
    AI_REFERENCE_FRAME_MAX_SIDE: int = 512
    # Total images per AI request: user frames + reference examples
    AI_MAX_IMAGES: int = 30
    REFERENCE_VIDEOS_FOLDER: str = "../hasl_files"
    REFERENCE_FRAMES_FOLDER: str = "data/reference_frames"
    REFERENCE_INDEX_PATH: str = "data/reference_index.json"

    # File Storage
    UPLOAD_FOLDER: str = "data/uploads"
    TEMP_FOLDER: str = "data/temp"
    SCREENSHOTS_FOLDER: str = "data/screenshots"
    MAX_UPLOAD_SIZE: int = 1073741824  # 1GB
    MAX_VIDEO_DURATION: int = 600  # 10 minutes
    TEMP_UPLOAD_TTL_HOURS: int = 24

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

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

    @field_validator("AI_PROVIDER")
    @classmethod
    def validate_ai_provider(cls, v):
        """Validate AI_PROVIDER is a supported provider."""
        v = v.strip().lower()
        if v not in ("grok_cli", "claude", "claude_cli"):
            raise ValueError("AI_PROVIDER must be 'grok_cli', 'claude_cli' or 'claude'")
        return v


# Singleton instance
settings = Settings()
