"""POST /query: retrieval, generation and a trace row, with a fake model (AC-OBS-01, AC-GRD-02)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from docdesk.api.query_deps import get_answer_prompt, get_encoder, get_llm, get_token_counter
from docdesk.core.config import Settings
from docdesk.core.errors import AppError
from docdesk.db.models.traces import QueryTraceRow
from docdesk.db.session import make_engine, make_session_factory
from docdesk.llm.errors import LLMTimeoutError
from docdesk.prompts.loader import load_prompt
from fakes.corpus import Corpus, FixedEncoder
from fakes.ingestion import WordCounter
from fakes.llm import FakeLLMClient

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[2]
CREDS = {"email": "asker@example.com", "password": "a-long-enough-password"}
REPLY = json.dumps(
    {
        "evidence_used": ["c1"],
        "answer": "Aspirin may cause stomach bleeding.",
        "citations": ["c1"],
        "confidence": "high",
        "abstained": False,
        "abstain_reason": "none",
    }
)


@pytest.fixture
def me(client: TestClient) -> dict[str, str]:
    user_id = client.post("/auth/register", json=CREDS).json()["data"]["id"]
    token = client.post("/auth/login", json=CREDS).json()["data"]["access_token"]
    return {"authorization": f"Bearer {token}", "user_id": user_id}


@pytest.fixture
def wire(client: TestClient):
    """Replace the model, encoder and prompt lookup with fakes; return the fake LLM."""

    def install(replies: list[str | Exception]) -> FakeLLMClient:
        fake = FakeLLMClient(replies)
        overrides = client.app.dependency_overrides  # type: ignore[attr-defined]
        overrides[get_llm] = lambda: fake
        overrides[get_encoder] = lambda: FixedEncoder(0)
        overrides[get_token_counter] = lambda: WordCounter()
        overrides[get_answer_prompt] = lambda: load_prompt(ROOT / "prompts/answer/answer.v1.md")
        return fake

    return install


@pytest.fixture
def seed(migrated_url: str):
    """Write one ready document with one chunk for an owner, committed for the API to read."""
    engine = make_engine(migrated_url)

    def make(owner_id: str | None = None, text: str = "Aspirin may cause stomach bleeding."):
        with make_session_factory(engine)() as session:
            corpus = Corpus(session)
            owner = uuid.UUID(owner_id) if owner_id else corpus.user()
            corpus.chunk(corpus.document(owner, "Aspirin label"), text, hot=0)
            session.commit()
            return owner

    yield make
    engine.dispose()


def trace_for(migrated_url: str, trace_id: str) -> QueryTraceRow:
    engine = make_engine(migrated_url)
    with make_session_factory(engine)() as session:
        row = session.execute(
            select(QueryTraceRow).where(QueryTraceRow.trace_id == trace_id)
        ).scalar_one()
    engine.dispose()
    return row


def ask(client: TestClient, me: dict[str, str], question: str = "What are aspirin risks?"):
    return client.post(
        "/query", json={"question": question}, headers={"authorization": me["authorization"]}
    )


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
