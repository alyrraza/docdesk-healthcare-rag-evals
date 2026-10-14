"""POST /retrieve: ranked chunks with scores and no model call, for the web page."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from docdesk.api.query_deps import get_encoder
from fakes.corpus import FixedEncoder
from fakes.query_api import register_user

pytestmark = pytest.mark.integration


def post(client: TestClient, headers: dict[str, str] | None, question: str = "aspirin risks"):
    """Send one retrieve request, with or without the auth header."""
    return client.post("/retrieve", json={"question": question}, headers=headers or {})


def test_ac_web_01_retrieve_needs_a_login(client: TestClient) -> None:
    assert post(client, None).status_code == 401


def test_ac_web_02_retrieve_returns_chunks_with_title_and_score_and_no_model_call(
    client: TestClient, me: dict[str, str], seed
) -> None:
    client.app.dependency_overrides[get_encoder] = lambda: FixedEncoder(0)  # type: ignore[attr-defined]
    seed(me["user_id"])
    response = post(client, {"authorization": me["authorization"]})
    assert response.status_code == 200
    chunk = response.json()["data"]["chunks"][0]
    assert chunk["document_title"] == "Aspirin label"
    assert chunk["text"] == "Aspirin may cause stomach bleeding."
    assert isinstance(chunk["score"], float)


def test_ac_web_03_retrieve_never_shows_another_users_private_document(
    client: TestClient, me: dict[str, str], seed
) -> None:
    client.app.dependency_overrides[get_encoder] = lambda: FixedEncoder(0)  # type: ignore[attr-defined]
    seed(me["user_id"], text="Zorbaxin private result.", title="A private notes")
    other = register_user(client, "second@example.com")
    body = post(client, {"authorization": other["authorization"]}).json()
    assert body["data"]["chunks"] == []
    assert "Zorbaxin" not in json.dumps(body)
