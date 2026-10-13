"""Application settings read from environment variables only."""

from __future__ import annotations

from functools import lru_cache
from typing import ClassVar
from urllib.parse import unquote, urlsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Words that mean "someone copied the example file and forgot to put in a real secret".
PLACEHOLDER_WORDS = ("change-me", "changeme", "example", "placeholder")


def placeholder_word_in(secret: str) -> str | None:
    """Return the placeholder word found in a secret (ignoring case), or None."""
    lowered = secret.lower()
    return next((word for word in PLACEHOLDER_WORDS if word in lowered), None)


def url_password(url: str) -> str | None:
    """Extract only the password part of a connection url."""
    try:
        password = urlsplit(url).password
    except ValueError:
        return None
    return unquote(password) if password else None


class Settings(BaseSettings):
    """One typed place for configuration so a missing value stops the app at startup."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    # Tests flip this on the class (monkeypatch). It is a ClassVar, so no environment
    # variable or .env line can switch the check off in a real deployment.
    reject_placeholders: ClassVar[bool] = True

    database_url: str
    redis_url: str
    # Login for the SQL branch's read-only role; optional until that branch exists.
    readonly_database_url: str | None = None
    jwt_secret: str = Field(min_length=32)
    jwt_lifetime_minutes: int = Field(default=30, gt=0)
    # Only scripts/seed_admin.py uses these; checked here so a placeholder never gets seeded.
    admin_email: str | None = None
    admin_password: str | None = None

    @model_validator(mode="after")
    def refuse_placeholder_secrets(self) -> Settings:
        """Stop startup when a secret still holds a value copied from .env.example."""
        if not self.reject_placeholders:
            return self
        secrets = {
            "JWT_SECRET": self.jwt_secret,
            "ADMIN_PASSWORD": self.admin_password,
            "DATABASE_URL": url_password(self.database_url),
            "READONLY_DATABASE_URL": url_password(self.readonly_database_url or ""),
            "REDIS_URL": url_password(self.redis_url),
        }
        problems = [
            f"{name} contains the placeholder word '{word}'"
            for name, secret in secrets.items()
            if secret and (word := placeholder_word_in(secret))
        ]
        if problems:
            raise ValueError("; ".join(problems) + ". Put a real secret in .env.")
        return self


@lru_cache
def get_settings() -> Settings:
    """Build settings once per process so every caller sees the same values."""
    return Settings()
