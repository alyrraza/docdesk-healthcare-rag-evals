"""Application settings read from environment variables only."""

from __future__ import annotations

from functools import lru_cache
from typing import ClassVar, Literal
from urllib.parse import unquote, urlsplit

from pydantic import Field, SecretStr, model_validator
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

    # "production" turns off the public API docs; local and test keep them on.
    environment: Literal["local", "test", "production"] = "local"
    database_url: str
    redis_url: str
    # Login for the SQL branch's read-only role; optional until that branch exists.
    readonly_database_url: str | None = None
    # Where uploaded files and the downloaded embedding model live (both git-ignored).
    upload_dir: str = "data/uploads"
    model_dir: str = ".cache/models/all-MiniLM-L6-v2"
    # Largest accepted upload in bytes; the body is read up to this size and no further.
    max_upload_bytes: int = Field(default=5_000_000, gt=0)
    # Free-tier LLM keys; optional so the app and every test run without them.
    groq_api_key: SecretStr | None = None
    # A second Groq account of the same owner; the eval key pool switches to it at the daily limit.
    groq_api_key_2: SecretStr | None = None
    openrouter_api_key: SecretStr | None = None
    # Model ids are fixed here and logged with every result. Generator and judge must differ.
    generator_model: str = "openai/gpt-oss-120b"
    judge_model: str = "qwen/qwen3.8-27b"
    # Only for the 40 item judge calibration cross check, free models only.
    crosscheck_judge_model: str = "google/gemma-4-31b-it:free"
    crosscheck_fallback_model: str = "nvidia/nemotron-3-super-120b-a12b:free"
    jwt_secret: str = Field(min_length=32)
    jwt_lifetime_minutes: int = Field(default=30, gt=0)
    # Only scripts/seed_admin.py uses these; checked here so a placeholder never gets seeded.
    admin_email: str | None = None
    admin_password: str | None = None

    @property
    def groq_api_keys(self) -> list[str]:
        """Why: the eval key pool needs every configured Groq key, in slot order, as plain text."""
        keys = (self.groq_api_key, self.groq_api_key_2)
        return [k.get_secret_value() for k in keys if k is not None and k.get_secret_value()]

    @property
    def public_docs_enabled(self) -> bool:
        """Serve /docs, /redoc and /openapi.json everywhere except production."""
        return self.environment != "production"

    @model_validator(mode="after")
    def check_model_choices(self) -> Settings:
        """Stop startup if the judge could grade its own family or a paid model slips in."""
        if self.generator_model == self.judge_model:
            raise ValueError("GENERATOR_MODEL and JUDGE_MODEL must be different models")
        for name in (self.crosscheck_judge_model, self.crosscheck_fallback_model):
            if not name.endswith(":free") or name.startswith("openrouter/"):
                raise ValueError(
                    f"cross check model '{name}' must be a named model ending in :free"
                )
        return self

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
