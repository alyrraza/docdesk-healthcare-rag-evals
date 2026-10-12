"""Fixtures for tests that need the schema: migrate once, roll back after each test."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session

from docdesk.db.session import make_engine, make_session_factory

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def migrated_url(test_database_url: str) -> str:
    """Build the schema from scratch with the real migrations, so tests check them too."""
    config = Config(str(ROOT / "alembic.ini"))
    config.attributes["url"] = test_database_url
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    return test_database_url


@pytest.fixture
def db_session(migrated_url: str) -> Iterator[Session]:
    """Give each test its own session and undo everything it wrote."""
    engine = make_engine(migrated_url)
    with make_session_factory(engine)() as session:
        yield session
        session.rollback()
    engine.dispose()
