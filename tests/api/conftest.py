"""API test fixtures: a client wired to the test database and cleaned after each test."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from docdesk.api.app import create_app
from docdesk.api.query_deps import get_answer_prompt, get_encoder, get_llm, get_token_counter
from docdesk.core.config import Settings, get_settings
from docdesk.db.session import get_session, make_engine, make_session_factory
from docdesk.prompts.loader import load_prompt
from fakes.corpus import Corpus, FixedEncoder
from fakes.ingestion import WordCounter
from fakes.llm import FakeLLMClient
from fakes.query_api import register_user

ROOT = Path(__file__).resolve().parents[2]

API_SETTINGS = Settings(
    database_url="postgresql://unused",
    redis_url="redis://unused",
    jwt_secret="t" * 40,
    _env_file=None,
)


@pytest.fixture(autouse=True)
def app_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Let create_app() with no argument build from test settings, not a real .env."""
    monkeypatch.setattr("docdesk.api.app.get_settings", lambda: API_SETTINGS)


@pytest.fixture
def api_settings() -> Settings:
    """The settings the test client uses, so tests can verify tokens it issued."""
    return API_SETTINGS


@pytest.fixture
def client(migrated_url: str) -> Iterator[TestClient]:
    """App whose sessions use the test database; users written by a test are removed after."""
    engine = make_engine(migrated_url)
    factory = make_session_factory(engine)

    def session_override() -> Iterator:
        with factory() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: API_SETTINGS
    yield TestClient(app)
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM users"))
    engine.dispose()


@pytest.fixture
def me(client: TestClient) -> dict[str, str]:
    """A registered and logged in user for POST /query tests."""
    return register_user(client, "asker@example.com")


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

    def make(
        owner_id: str | None = None,
        text: str = "Aspirin may cause stomach bleeding.",
        title: str = "Aspirin label",
    ):
        with make_session_factory(engine)() as session:
            corpus = Corpus(session)
            owner = uuid.UUID(owner_id) if owner_id else corpus.user()
            corpus.chunk(corpus.document(owner, title), text, hot=0)
            session.commit()
            return owner

    yield make
    engine.dispose()
