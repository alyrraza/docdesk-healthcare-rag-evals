"""Fixtures for tests that need the schema: migrate once, roll back after each test."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session

from docdesk.db.session import make_engine, make_session_factory


@pytest.fixture
def db_session(migrated_url: str) -> Iterator[Session]:
    """Give each test its own session and undo everything it wrote."""
    engine = make_engine(migrated_url)
    with make_session_factory(engine)() as session:
        yield session
        session.rollback()
    engine.dispose()
