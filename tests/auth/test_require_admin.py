"""Tests for require_admin (AC-AUTH-04)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from docdesk.auth.deps import require_admin
from docdesk.auth.jwt import TokenClaims, create_token
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

    @app.get("/admin/ping")
    def ping(claims: TokenClaims = Depends(require_admin)) -> dict[str, str]:
        return {"role": claims.role}

    return TestClient(app)


def headers_for(role: str) -> dict[str, str]:
    user = User(uuid.uuid4(), "a@example.com", "h", role, datetime.now(UTC))
    return {"Authorization": f"Bearer {create_token(user, SETTINGS)}"}


def test_ac_auth_04_non_admin_gets_403_envelope() -> None:
    response = build_client().get("/admin/ping", headers=headers_for("user"))
    assert response.status_code == 403
    error = response.json()["error"]
    assert error["code"] == "forbidden"
    assert "trace_id" in error


def test_ac_auth_04_admin_is_allowed() -> None:
    response = build_client().get("/admin/ping", headers=headers_for("admin"))
    assert response.status_code == 200


def test_ac_auth_04_missing_token_is_401_not_403() -> None:
    assert build_client().get("/admin/ping").status_code == 401
