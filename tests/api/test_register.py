"""Tests for POST /auth/register (AC-AUTH-01)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from docdesk.db.session import make_engine

pytestmark = pytest.mark.integration

GOOD = {"email": "Reg.User@Example.com", "password": "a-long-enough-password"}


def test_register_creates_a_user_role_with_201(client: TestClient) -> None:
    response = client.post("/auth/register", json=GOOD)
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["email"] == "reg.user@example.com"
    assert data["role"] == "user"
    assert "password" not in response.text
    assert "hash" not in response.text


def test_ac_auth_01_register_stores_a_hash_and_never_the_password(
    client: TestClient, migrated_url: str
) -> None:
    client.post("/auth/register", json=GOOD)
    with make_engine(migrated_url).connect() as connection:
        stored = connection.execute(text("SELECT password_hash FROM users")).scalar_one()
    assert stored != GOOD["password"]
    assert GOOD["password"] not in stored
    assert stored.startswith("$argon2")


def test_register_cannot_choose_the_admin_role(client: TestClient) -> None:
    response = client.post("/auth/register", json={**GOOD, "role": "admin"})
    assert response.status_code == 201
    assert response.json()["data"]["role"] == "user"


def test_duplicate_email_gives_409_envelope(client: TestClient) -> None:
    client.post("/auth/register", json=GOOD)
    response = client.post("/auth/register", json={**GOOD, "email": "reg.user@example.com"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_taken"


@pytest.mark.parametrize(
    "body",
    [
        {"email": "not-an-email", "password": "a-long-enough-password"},
        {"email": "a@example.com", "password": "short"},
        {"email": "a@example.com", "password": "x" * 200},
        {"email": "a@example.com"},
        {},
    ],
)
def test_bad_input_gives_422_envelope(client: TestClient, body: dict) -> None:
    response = client.post("/auth/register", json=body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
