"""Tests for POST /auth/login (AC-AUTH-02)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from docdesk.auth.jwt import decode_token
from docdesk.core.config import Settings

pytestmark = pytest.mark.integration

CREDS = {"email": "login.user@example.com", "password": "a-long-enough-password"}


def register(client: TestClient) -> str:
    return client.post("/auth/register", json=CREDS).json()["data"]["id"]


def test_ac_auth_02_login_returns_a_token_with_sub_role_exp(
    client: TestClient, api_settings: Settings
) -> None:
    user_id = register(client)
    response = client.post("/auth/login", json=CREDS)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["token_type"] == "bearer"
    claims = decode_token(data["access_token"], api_settings)
    assert str(claims.user_id) == user_id
    assert claims.role == "user"


def test_login_ignores_email_case(client: TestClient) -> None:
    register(client)
    body = {**CREDS, "email": "LOGIN.USER@example.com"}
    assert client.post("/auth/login", json=body).status_code == 200


def test_wrong_password_and_unknown_email_look_the_same(client: TestClient) -> None:
    register(client)
    wrong = client.post("/auth/login", json={**CREDS, "password": "not-the-password"})
    unknown = client.post("/auth/login", json={**CREDS, "email": "ghost@example.com"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["error"]["code"] == "invalid_credentials"
    assert wrong.json()["error"]["message"] == unknown.json()["error"]["message"]


def test_login_with_missing_fields_gives_422_envelope(client: TestClient) -> None:
    response = client.post("/auth/login", json={"email": "a@example.com"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
