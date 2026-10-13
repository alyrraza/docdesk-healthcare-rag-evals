"""Two users on the real POST /query route: one never sees the other's private document."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from fakes.query_api import REPLY, ask, register_user, trace_for

pytestmark = pytest.mark.integration

SECRET = "Zorbaxin private lab result for user A only."


def test_ac_ret_05_a_private_document_never_reaches_another_users_evidence_or_answer(
    client: TestClient, me: dict[str, str], wire, seed, migrated_url: str
) -> None:
    fake = wire([REPLY])
    seed(me["user_id"], text=SECRET, title="A private notes")
    user_b = register_user(client, "second@example.com")
    response = ask(client, user_b, "What does the Zorbaxin lab result say?")
    body = response.json()
    assert response.status_code == 200
    assert body["data"]["abstained"] is True and body["data"]["citations"] == []
    assert fake.requests == []  # nothing was retrieved, so the model was never shown anything
    assert "Zorbaxin" not in json.dumps(body) and "A private notes" not in json.dumps(body)
    row = trace_for(migrated_url, body["trace_id"])
    assert row.retrieved == [] and row.used_ids == []


def test_ac_ret_05_user_b_with_own_and_shared_documents_still_never_sees_user_as(
    client: TestClient, me: dict[str, str], wire, seed
) -> None:
    fake = wire([REPLY])
    seed(me["user_id"], text=SECRET, title="A private notes")
    user_b = register_user(client, "second@example.com")
    seed(user_b["user_id"], text="Aspirin may cause stomach bleeding.", title="B label")
    body = ask(client, user_b, "What are the aspirin risks according to my lab notes?").json()
    sent = fake.requests[0]
    assert "Zorbaxin" not in sent.system + sent.user
    assert "A private notes" not in sent.system + sent.user
    assert [c["document_title"] for c in body["data"]["citations"]] == ["B label"]
    assert "Zorbaxin" not in json.dumps(body)


def test_ac_ret_05_the_owner_still_gets_their_own_private_document(
    client: TestClient, me: dict[str, str], wire, seed
) -> None:
    fake = wire([REPLY])
    seed(me["user_id"], text=SECRET, title="A private notes")
    body = ask(client, me, "What does the Zorbaxin lab result say?").json()
    assert "Zorbaxin" in fake.requests[0].user
    assert body["data"]["citations"][0]["document_title"] == "A private notes"
