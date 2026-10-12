"""Application settings read from environment variables only."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """One typed place for configuration so a missing value stops the app at startup."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str
    # Login for the SQL branch's read-only role; optional until that branch exists.
    readonly_database_url: str | None = None
    jwt_secret: str = Field(min_length=32)
    jwt_lifetime_minutes: int = Field(default=30, gt=0)


@lru_cache
def get_settings() -> Settings:
    """Build settings once per process so every caller sees the same values."""
    return Settings()
