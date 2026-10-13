"""Settings must refuse to start with placeholder secrets."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from docdesk.core.config import Settings

ROOT = Path(__file__).resolve().parents[2]
REAL_JWT = "f3a9c1d27b8e4a60915d2c7e8b4f1a36d0e9c5b7a2f84163"
REAL_DB = "postgresql://owner:Vq8x2LmP4rTz@db.internal:5432/docdesk"


def build(**overrides: str | None) -> Settings:
    values = {
        "database_url": REAL_DB,
        "redis_url": "redis://localhost:6379/0",
        "jwt_secret": REAL_JWT,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.mark.parametrize(
    "secret",
    [
        "change-me-change-me-change-me-change-me",
        "CHANGE-ME-with-something-long-enough-1234",
        "my-changeme-secret-that-is-long-enough-99",
        "this-is-an-example-secret-of-length-40-ok",
        "PlaceHolder-value-that-is-long-enough-0000",
    ],
)
def test_placeholder_jwt_secret_stops_startup(secret: str) -> None:
    with pytest.raises(ValidationError) as caught:
        build(jwt_secret=secret)
    assert "JWT_SECRET" in str(caught.value)


@pytest.mark.parametrize("password", ["change-me-change-me", "Example1234567", "changeme"])
def test_placeholder_admin_password_stops_startup(password: str) -> None:
    with pytest.raises(ValidationError) as caught:
        build(admin_password=password)
    assert "ADMIN_PASSWORD" in str(caught.value)


@pytest.mark.parametrize("field", ["database_url", "readonly_database_url"])
def test_placeholder_password_inside_a_database_url_stops_startup(field: str) -> None:
    url = "postgresql://owner:change-me@db.internal:5432/docdesk"
    with pytest.raises(ValidationError) as caught:
        build(**{field: url})
    assert field.upper() in str(caught.value)


def test_error_message_names_the_field_but_not_the_secret_value() -> None:
    with pytest.raises(ValidationError) as caught:
        build(jwt_secret="change-me-change-me-change-me-change-me")
    assert "change-me-change-me-change-me-change-me" not in str(caught.value)


def test_words_outside_the_password_do_not_trigger_the_check() -> None:
    settings = build(
        database_url="postgresql://example_user:Vq8x2LmP4rTz@example.com:5432/example_db",
        admin_password="a-genuinely-strong-passphrase-77",
    )
    assert settings.admin_password == "a-genuinely-strong-passphrase-77"


def test_missing_optional_secrets_are_allowed() -> None:
    settings = build()
    assert settings.admin_password is None
    assert settings.readonly_database_url is None


def test_env_example_is_rejected_by_default() -> None:
    with pytest.raises(ValidationError) as caught:
        Settings(_env_file=ROOT / ".env.example")
    message = str(caught.value)
    for name in ("DATABASE_URL", "READONLY_DATABASE_URL", "JWT_SECRET", "ADMIN_PASSWORD"):
        assert name in message


def test_env_example_loads_only_through_an_explicit_test_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(Settings, "reject_placeholders", False)
    settings = Settings(_env_file=ROOT / ".env.example")
    assert settings.jwt_lifetime_minutes == 30


def test_the_check_cannot_be_switched_off_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("REJECT_PLACEHOLDERS", "false")
    with pytest.raises(ValidationError):
        build(jwt_secret="change-me-change-me-change-me-change-me")
