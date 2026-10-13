"""Fixtures for pipeline tests: a real database whose commits are cleaned up afterwards."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterator

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from docdesk.db.repositories.documents import Document, DocumentRepository
from docdesk.db.repositories.users import UserRepository
from docdesk.db.session import make_engine, make_session_factory
from fakes.ingestion import FakeStore


@pytest.fixture
def pipeline_session(migrated_url: str) -> Iterator[Session]:
    """A session whose commits are real, so the test cleans up by deleting its users."""
    engine = make_engine(migrated_url)
    with make_session_factory(engine)() as session:
        yield session
        session.rollback()
        session.execute(text("DELETE FROM users"))
        session.commit()
    engine.dispose()


@pytest.fixture
def store() -> FakeStore:
    return FakeStore()


@pytest.fixture
def make_document(pipeline_session: Session, store: FakeStore) -> Callable[[bytes], Document]:
    """Create a queued document whose file content is the given bytes."""

    def make(data: bytes) -> Document:
        unique = uuid.uuid4().hex
        owner = UserRepository(pipeline_session).add(f"{unique}@example.com", "hash", "user")
        document = DocumentRepository(pipeline_session).add(owner.id, "label", "upload", unique)
        pipeline_session.commit()
        store.files[document.id] = data
        return document

    return make
