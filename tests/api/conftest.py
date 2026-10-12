"""API test fixtures: a client wired to the test database and cleaned after each test."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from docdesk.api.app import create_app
from docdesk.core.config import Settings, get_settings
from docdesk.db.session import get_session, make_engine, make_session_factory

API_SETTINGS = Settings(
    database_url="postgresql://unused",
    redis_url="redis://unused",
    jwt_secret="t" * 40,
    _env_file=None,
)


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
