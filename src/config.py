import os
from typing import Literal

from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: Literal["local", "dev", "qas", "prod"] = "local"
    LOCAL_API_TOKEN: str | None = None

    # LLM — Ollama for local, Anthropic or OpenAI for cloud
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"
    LLM_PROVIDER: Literal["anthropic", "openai"] = "anthropic"
    LLM_MODEL: str = "claude-sonnet-4-6"
    ANTHROPIC_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None

    # Storage
    MCP_BASE_URL: str = "http://localhost:8000"
    DB_PATH: str = "brew.db"
    CHECKPOINT_DB_PATH: str = "brew_checkpoints.db"
    CHECKPOINT_MAX_THREADS: int = 500

    # Observability (optional, graceful no-op when disabled)
    LANGFUSE_ENABLED: bool = False
    LANGFUSE_HOST: str | None = None
    LANGFUSE_PUBLIC_KEY: str | None = None
    LANGFUSE_SECRET_KEY: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings.model_validate({})

# pydantic-settings reads .env into the Settings object but does not populate
# os.environ, so libraries that read env vars directly (like langchain) would miss them.
if settings.ANTHROPIC_API_KEY:
    os.environ.setdefault("ANTHROPIC_API_KEY", settings.ANTHROPIC_API_KEY)
if settings.OPENAI_API_KEY:
    os.environ.setdefault("OPENAI_API_KEY", settings.OPENAI_API_KEY)
