from __future__ import annotations

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ENCRYPTION_KEY: str = ""
    ENCRYPTION_KEY_OLD: Optional[str] = None
    MCP_API_KEY: str = "dev-mcp-key"
    MCP_REQUIRE_AUTH: bool = True

    # Database
    DATABASE_URL: str = (
        "postgresql+asyncpg://socialmind:socialmind@localhost:5432/socialmind"
    )
    POSTGRES_PASSWORD: str = "socialmind"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_SESSION_ENABLED: bool = True
    REDIS_SESSION_TTL: int = 60 * 60 * 24

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "socialmind"
    MINIO_SECRET_KEY: str = "socialmind"
    MINIO_SECURE: bool = False

    # LLM
    LLM_PROVIDER: str = "ollama"
    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"
    EMBED_PROVIDER: str = "ollama"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-haiku-20240307"
    LITELLM_MODEL: Optional[str] = None
    LITELLM_BASE_URL: Optional[str] = None

    # Image generation
    IMAGE_PROVIDER: str = "dalle"
    SD_API_URL: str = "http://localhost:7860"

    # CAPTCHA
    CAPTCHA_SOLVER: str = "2captcha"
    CAPTCHA_API_KEY: Optional[str] = None

    # ChromaDB
    CHROMADB_URL: str = "http://localhost:8002"

    # App
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Flower
    FLOWER_PASSWORD: str = "flower"


settings = Settings()
