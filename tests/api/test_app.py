"""Tests for api/app.py and the health route."""

from __future__ import annotations

from fastapi.testclient import TestClient

from docdesk.api.app import create_app
from docdesk.core.errors import AppError


def test_health_returns_ok_in_the_success_envelope() -> None:
    response = TestClient(create_app()).get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["data"] == {"status": "ok"}
    assert body["trace_id"] == response.headers["x-trace-id"]


def test_each_request_gets_a_new_trace_id() -> None:
    client = TestClient(create_app())
    first = client.get("/health").headers["x-trace-id"]
    second = client.get("/health").headers["x-trace-id"]
    assert first != second


def test_error_envelope_carries_the_same_trace_id_as_the_header() -> None:
    app = create_app()

    @app.get("/boom")
    def boom() -> None:
        raise AppError(code="forbidden", message="No", status=403)

    response = TestClient(app).get("/boom")
    assert response.status_code == 403
    assert response.json()["error"]["trace_id"] == response.headers["x-trace-id"]


def test_unknown_route_uses_the_error_envelope() -> None:
    response = TestClient(create_app()).get("/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
