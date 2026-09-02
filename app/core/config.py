from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Beezents API"
    app_version: str = "0.1.0"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/beezents"

    session_cookie_name: str = "beezents_session"
    session_max_age_seconds: int = 7 * 24 * 60 * 60
    cookie_secure: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
