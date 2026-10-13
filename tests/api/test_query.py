"""POST /query: retrieval, generation and a trace row, with a fake model (AC-OBS-01, AC-GRD-02)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from docdesk.api.query_deps import get_llm
from docdesk.core.config import Settings
from docdesk.core.errors import AppError
from docdesk.guardrails.policy import REFUSAL_MESSAGE
from docdesk.llm.errors import LLMTimeoutError
from fakes.query_api import REPLY, ask, trace_for

pytestmark = pytest.mark.integration


def test_ac_gen_01_a_question_gets_an_answer_with_citations_and_the_disclaimer(
    client: TestClient, me: dict[str, str], wire, seed, migrated_url: str
) -> None:
    fake = wire([REPLY])
    seed(me["user_id"])
    response = ask(client, me)
    assert response.status_code == 200
    body = response.json()
    data = body["data"]
    assert data["answer"] == "Aspirin may cause stomach bleeding."
    assert "not medical advice" in data["disclaimer"]
    assert data["abstained"] is False
    assert data["citations"][0]["document_title"] == "Aspirin label"
    assert data["citations"][0]["text"] == "Aspirin may cause stomach bleeding."
    assert body["trace_id"] == response.headers["x-trace-id"]
    assert len(fake.requests) == 1


def test_ac_obs_01_every_request_leaves_one_trace_row_with_the_bundle_and_config_ids(
    client: TestClient, me: dict[str, str], wire, seed, migrated_url: str
) -> None:
    wire([REPLY])
    seed(me["user_id"])
    trace_id = ask(client, me).json()["trace_id"]
    row = trace_for(migrated_url, trace_id)
    assert row.config_id == "hybrid-n20-k5-rrf60"
    assert row.prompt_bundle_id and len(row.prompt_bundle_id) == 16
    assert len(row.used_ids) == 1 and row.tokens["model"] == "fake-model"
    assert str(row.user_id) == me["user_id"] and row.question_text is None
    assert row.guardrails == {"input": "allowed", "output": "passed"}


def test_ac_gen_03_a_user_with_no_matching_documents_gets_an_abstain_and_no_model_call(
    client: TestClient, me: dict[str, str], wire, seed, migrated_url: str
) -> None:
    fake = wire([])
    seed()  # a document owned by somebody else
    response = ask(client, me)
    data = response.json()["data"]
    assert data["abstained"] is True and data["abstain_reason"] == "no_evidence"
    assert data["citations"] == [] and fake.requests == []
    assert trace_for(migrated_url, response.json()["trace_id"]).abstained is True


def test_ac_gen_04_a_model_failure_returns_the_typed_fallback_and_a_trace(
    client: TestClient, me: dict[str, str], wire, seed, migrated_url: str
) -> None:
    wire([LLMTimeoutError("slow")])
    seed(me["user_id"])
    response = ask(client, me)
    assert response.status_code == 200
    assert response.json()["data"]["abstain_reason"] == "system_error"
    assert trace_for(migrated_url, response.json()["trace_id"]).error_code == "llm_timeout"


def test_ac_auth_03_a_query_without_a_token_is_401(client: TestClient) -> None:
    assert client.post("/query", json={"question": "hi there"}).status_code == 401


@pytest.mark.parametrize("question", ["", "   ", "x" * 1001])
def test_ac_grd_02_an_empty_or_too_long_question_is_422(
    client: TestClient, me: dict[str, str], wire, question: str
) -> None:
    wire([])
    assert ask(client, me, question).status_code == 422


def test_ac_gen_01_a_missing_groq_key_is_a_clear_503_not_a_crash() -> None:
    settings = Settings(
        database_url="postgresql://owner:Vq8x2LmP4rTz@db.internal/docdesk",
        redis_url="redis://localhost:6380/0",
        jwt_secret="f3a9c1d27b8e4a60915d2c7e8b4f1a36d0e9c5b7a2f84163",
        _env_file=None,
    )
    with pytest.raises(AppError) as caught:
        get_llm(settings)
    assert caught.value.status == 503 and caught.value.code == "llm_not_configured"


def test_ac_gen_05_a_personal_dose_question_is_refused_with_the_policy_message_and_no_model_call(
    client: TestClient, me: dict[str, str], wire, seed, migrated_url: str
) -> None:
    fake = wire([])
    seed(me["user_id"])
    response = ask(client, me, "What dose of famotidine should I take for my stomach pain?")
    data = response.json()["data"]
    assert response.status_code == 200
    assert data["abstained"] is True and data["abstain_reason"] == "unsafe_request"
    assert data["answer"] == REFUSAL_MESSAGE and "not medical advice" in data["disclaimer"]
    assert data["citations"] == [] and fake.requests == []
    row = trace_for(migrated_url, response.json()["trace_id"])
    assert row.abstain_reason == "unsafe_request"
    assert row.guardrails == {"input": "refused", "reason": "personal_dose"}
    assert row.retrieved == []


def test_ac_gen_05_a_what_does_the_label_say_dose_question_is_still_answered(
    client: TestClient, me: dict[str, str], wire, seed, migrated_url: str
) -> None:
    fake = wire([REPLY])
    seed(me["user_id"])
    response = ask(client, me, "What does the aspirin label say about the recommended dose?")
    data = response.json()["data"]
    assert data["abstained"] is False and data["citations"]
    assert len(fake.requests) == 1
    row = trace_for(migrated_url, response.json()["trace_id"])
    assert row.guardrails == {"input": "allowed"}
