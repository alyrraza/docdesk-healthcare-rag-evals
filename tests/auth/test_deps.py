"""Tests for auth/roles.py and auth/deps.py require_user (AC-AUTH-03)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from docdesk.auth.deps import require_user
from docdesk.auth.jwt import TokenClaims, create_token
from docdesk.auth.roles import Role
from docdesk.core import clock
from docdesk.core.config import Settings, get_settings
from docdesk.core.errors import register_error_handlers
from docdesk.db.repositories.users import User

SETTINGS = Settings(
    database_url="postgresql://x",
    redis_url="redis://x",
    jwt_secret="k" * 40,
    _env_file=None,
)


def build_client() -> TestClient:
    app = FastAPI()
    register_error_handlers(app)
    app.dependency_overrides[get_settings] = lambda: SETTINGS

    @app.get("/me")
    def me(claims: TokenClaims = Depends(require_user)) -> dict[str, str]:
        return {"role": claims.role}

    return TestClient(app)


def token_for(role: str = "user") -> str:
    user = User(uuid.uuid4(), "a@example.com", "h", role, datetime.now(UTC))
    return create_token(user, SETTINGS)


def assert_unauthorized(response) -> None:
    assert response.status_code == 401
    error = response.json()["error"]
    assert error["code"] == "unauthorized"
    assert "trace_id" in error


def test_role_enum_values() -> None:
    assert {r.value for r in Role} == {"user", "admin"}


def test_ac_auth_03_missing_token_gives_401_envelope() -> None:
    assert_unauthorized(build_client().get("/me"))


def test_ac_auth_03_malformed_token_gives_401_envelope() -> None:
    response = build_client().get("/me", headers={"Authorization": "Bearer garbage"})
    assert_unauthorized(response)


def test_ac_auth_03_wrong_scheme_gives_401_envelope() -> None:
    response = build_client().get("/me", headers={"Authorization": "Basic abc"})
    assert_unauthorized(response)


def test_ac_auth_03_expired_token_gives_401_envelope(monkeypatch: pytest.MonkeyPatch) -> None:
    past = datetime.now(UTC) - timedelta(hours=2)
    monkeypatch.setattr(clock, "utc_now", lambda: past)
    token = token_for()
    monkeypatch.undo()
    response = build_client().get("/me", headers={"Authorization": f"Bearer {token}"})
    assert_unauthorized(response)


def test_valid_token_reaches_the_route() -> None:
    headers = {"Authorization": f"Bearer {token_for('admin')}"}
    response = build_client().get("/me", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"role": "admin"}
