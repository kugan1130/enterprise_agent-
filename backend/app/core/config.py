"""Application configuration settings using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    APP_NAME: str = "Enterprise Multi-Agent AI Assistant"
    MODEL_NAME: str = "llama-3.3-70b-versatile"
    GROQ_API_KEY: str = ""
    TAVILY_API_KEY: str = ""
    DATABASE_URL: str = "sqlite:///./enterprise_app.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    JWT_SECRET: str = "enterprise-secret-key-change-in-production-2026"
    ALLOWED_ORIGINS: str = "*"
    MAX_UPLOAD_SIZE_MB: int = 10
    DATA_DIR: Path = BASE_DIR / ".data"
    
    # LangSmith & MCP Tracing
    LANGCHAIN_TRACING_V2: str = "true"
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "enterprise-ai-assistant"
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"

    # Avoid the common system-level DEBUG variable
    DEBUG: bool = Field(default=False, validation_alias="APP_DEBUG")

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


if __name__ == "__main__":
    print("APP_NAME :", settings.APP_NAME)
    print("MODEL    :", settings.MODEL_NAME)
    print("DEBUG    :", settings.DEBUG)
