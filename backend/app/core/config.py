from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    GROQ_API_KEY: str
    TAVILY_API_KEY: str = ""
    DATABASE_URL: str = ""
    REDIS_URL: str = "redis://localhost:6379/0"
    MAX_MEMORY_MESSAGES: int = 10
    MODEL_NAME: str
    APP_NAME: str
    # Avoid the common system-level DEBUG variable, which may contain non-boolean
    # values such as "release" and prevent the application from starting.
    DEBUG: bool = Field(default=False, validation_alias="APP_DEBUG")

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    # Pydantic loads these required fields from the configured environment file.
    return Settings()  # pyright: ignore[reportCallIssue]


settings = get_settings()


if __name__ == "__main__":
    print("APP_NAME :", settings.APP_NAME)
    print("MODEL    :", settings.MODEL_NAME)
    print("DEBUG    :", settings.DEBUG)
    print("API KEY  :", settings.GROQ_API_KEY[:10] + "...")
