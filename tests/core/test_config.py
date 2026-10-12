"""Tests for core/config.py: settings come from the environment and fail fast."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from docdesk.core.config import Settings

REQUIRED = {
    "DATABASE_URL": "postgresql://u:p@localhost:5432/docdesk",
    "REDIS_URL": "redis://localhost:6379/0",
    "JWT_SECRET": "x" * 32,
}


def test_settings_load_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in REQUIRED.items():
        monkeypatch.setenv(key, value)
    settings = Settings(_env_file=None)
    assert settings.database_url == REQUIRED["DATABASE_URL"]
    assert settings.redis_url == REQUIRED["REDIS_URL"]
    assert settings.jwt_lifetime_minutes == 30


@pytest.mark.parametrize("missing", sorted(REQUIRED))
def test_missing_required_value_fails_at_startup(
    monkeypatch: pytest.MonkeyPatch, missing: str
) -> None:
    for key, value in REQUIRED.items():
        if key != missing:
            monkeypatch.setenv(key, value)
    monkeypatch.delenv(missing, raising=False)
    with pytest.raises(ValidationError) as caught:
        Settings(_env_file=None)
    assert missing.lower() in str(caught.value)


def test_short_jwt_secret_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in REQUIRED.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("JWT_SECRET", "short")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
