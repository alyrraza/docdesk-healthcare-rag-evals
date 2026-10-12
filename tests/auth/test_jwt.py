"""Tests for auth/jwt.py (AC-AUTH-02)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import jwt as pyjwt
import pytest

from docdesk.auth.jwt import TokenError, create_token, decode_token
from docdesk.core import clock
from docdesk.core.config import Settings
from docdesk.db.repositories.users import User

SECRET = "s" * 40


def make_settings(secret: str = SECRET, minutes: int = 30) -> Settings:
    return Settings(
        database_url="postgresql://x",
        redis_url="redis://x",
        jwt_secret=secret,
        jwt_lifetime_minutes=minutes,
        _env_file=None,
    )


def make_user(role: str = "user") -> User:
    return User(uuid.uuid4(), "a@example.com", "hash", role, datetime.now(UTC))


def test_ac_auth_02_token_carries_sub_role_and_exp() -> None:
    user = make_user("admin")
    claims = decode_token(create_token(user, make_settings()), make_settings())
    assert claims.user_id == user.id
    assert claims.role == "admin"
    raw = pyjwt.decode(create_token(user, make_settings()), SECRET, algorithms=["HS256"])
    assert set(raw) == {"sub", "role", "exp"}
    assert raw["sub"] == str(user.id)


def test_ac_auth_02_expiry_follows_the_configured_lifetime() -> None:
    token = create_token(make_user(), make_settings(minutes=5))
    raw = pyjwt.decode(token, SECRET, algorithms=["HS256"])
    remaining = raw["exp"] - datetime.now(UTC).timestamp()
    assert 4 * 60 < remaining <= 5 * 60


def test_ac_auth_02_expired_token_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    past = datetime.now(UTC) - timedelta(hours=2)
    monkeypatch.setattr(clock, "utc_now", lambda: past)
    token = create_token(make_user(), make_settings())
    monkeypatch.undo()
    with pytest.raises(TokenError):
        decode_token(token, make_settings())


def test_token_signed_with_another_secret_is_rejected() -> None:
    token = create_token(make_user(), make_settings(secret="o" * 40))
    with pytest.raises(TokenError):
        decode_token(token, make_settings())


def test_tampered_token_is_rejected() -> None:
    token = create_token(make_user(), make_settings())
    head, body, sig = token.split(".")
    with pytest.raises(TokenError):
        decode_token(f"{head}.{body}x.{sig}", make_settings())


def test_unsigned_alg_none_token_is_rejected() -> None:
    forged = pyjwt.encode({"sub": str(uuid.uuid4()), "role": "admin"}, None, algorithm="none")
    with pytest.raises(TokenError):
        decode_token(forged, make_settings())


def test_token_without_exp_is_rejected() -> None:
    forged = pyjwt.encode({"sub": str(uuid.uuid4()), "role": "user"}, SECRET, algorithm="HS256")
    with pytest.raises(TokenError):
        decode_token(forged, make_settings())


def test_garbage_and_bad_claims_are_rejected() -> None:
    with pytest.raises(TokenError):
        decode_token("not-a-jwt", make_settings())
    bad_sub = pyjwt.encode(
        {"sub": "not-a-uuid", "role": "user", "exp": datetime.now(UTC) + timedelta(minutes=5)},
        SECRET,
        algorithm="HS256",
    )
    with pytest.raises(TokenError):
        decode_token(bad_sub, make_settings())
    bad_role = pyjwt.encode(
        {"sub": str(uuid.uuid4()), "role": "root", "exp": datetime.now(UTC) + timedelta(minutes=5)},
        SECRET,
        algorithm="HS256",
    )
    with pytest.raises(TokenError):
        decode_token(bad_role, make_settings())
