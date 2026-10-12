"""Tests for core/errors.py: every error leaves the API in the standard envelope."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from docdesk.core.errors import AppError, register_error_handlers


def build_client() -> TestClient:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/boom")
    def boom() -> None:
        raise AppError(code="unauthorized", message="Token is missing", status=401)

    @app.get("/crash")
    def crash() -> None:
        raise RuntimeError("secret internal detail")

    @app.get("/number/{n}")
    def number(n: int) -> int:
        return n

    return TestClient(app, raise_server_exceptions=False)


def test_ac_auth_03_app_error_uses_the_standard_envelope() -> None:
    response = build_client().get("/boom")
    assert response.status_code == 401
    error = response.json()["error"]
    assert error["code"] == "unauthorized"
    assert error["message"] == "Token is missing"
    assert "trace_id" in error


def test_unexpected_error_hides_internal_detail() -> None:
    response = build_client().get("/crash")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "secret internal detail" not in response.text


def test_validation_error_uses_the_standard_envelope() -> None:
    response = build_client().get("/number/abc")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_unknown_route_uses_the_standard_envelope() -> None:
    response = build_client().get("/nope")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
