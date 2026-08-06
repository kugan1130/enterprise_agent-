from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    GROQ_API_KEY: str
    MODEL_NAME: str
    APP_NAME: str
    DEBUG: bool = False

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
    print("API KEY  :", settings.GROQ_API_KEY[:10] + "...")