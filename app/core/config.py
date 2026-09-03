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

    # Media / file storage
    # Storage backend name. "local" writes files under MEDIA_ROOT; future
    # backends (e.g. "s3", "r2") plug into the same StorageBackend interface.
    storage_backend: str = "local"
    # Local backend root directory for uploaded media (dev).
    media_root: str = "./media"
    # Maximum accepted upload size in bytes (10 MiB default).
    media_max_size_bytes: int = 10 * 1024 * 1024

    # API security
    # Comma-separated allowed CORS origins (e.g. "http://localhost:3000").
    # Empty = CORS disabled (same-origin / API-only clients).
    cors_allowed_origins: str = ""
    # Comma-separated allowed Host header values (e.g. "localhost,beezents.com").
    # Empty = Host validation disabled (development convenience).
    trusted_hosts: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
