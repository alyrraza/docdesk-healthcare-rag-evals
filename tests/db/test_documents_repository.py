"""Tests for the documents table and its repository."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from docdesk.db.models.documents import DocumentStatus
from docdesk.db.repositories.documents import DocumentRepository, DuplicateDocumentError
from docdesk.db.repositories.users import User, UserRepository

pytestmark = pytest.mark.integration


def make_user(session: Session, email: str = "owner@example.com") -> User:
    return UserRepository(session).add(email, "hash", "user")


def test_new_document_starts_queued_with_zero_chunks(db_session: Session) -> None:
    owner = make_user(db_session)
    doc = DocumentRepository(db_session).add(owner.id, "Aspirin label", "upload", "h1")
    assert doc.status == DocumentStatus.QUEUED
    assert doc.chunk_count == 0
    assert doc.fail_reason is None
    assert doc.is_shared is False


def test_get_returns_the_document_or_none(db_session: Session) -> None:
    owner = make_user(db_session)
    repo = DocumentRepository(db_session)
    doc = repo.add(owner.id, "t", "upload", "h1")
    assert repo.get(doc.id) == doc
    assert repo.get(uuid.uuid4()) is None


def test_ac_ing_04_same_owner_and_hash_is_a_duplicate(db_session: Session) -> None:
    owner = make_user(db_session)
    repo = DocumentRepository(db_session)
    first = repo.add(owner.id, "t", "upload", "same-hash")
    assert repo.find_by_hash(owner.id, "same-hash") == first
    with pytest.raises(DuplicateDocumentError):
        repo.add(owner.id, "other title", "upload", "same-hash")


def test_same_hash_for_different_owners_is_allowed(db_session: Session) -> None:
    repo = DocumentRepository(db_session)
    a = make_user(db_session, "a@example.com")
    b = make_user(db_session, "b@example.com")
    repo.add(a.id, "t", "upload", "h")
    repo.add(b.id, "t", "upload", "h")


def test_status_moves_and_records_chunk_count_and_reason(db_session: Session) -> None:
    owner = make_user(db_session)
    repo = DocumentRepository(db_session)
    doc = repo.add(owner.id, "t", "upload", "h1")
    ready = repo.set_status(doc.id, DocumentStatus.READY, chunk_count=12)
    assert (ready.status, ready.chunk_count) == (DocumentStatus.READY, 12)
    failed = repo.set_status(doc.id, DocumentStatus.FAILED, fail_reason="no text layer")
    assert failed.status == DocumentStatus.FAILED
    assert failed.fail_reason == "no text layer"


def test_list_visible_shows_own_and_shared_but_not_other_users(db_session: Session) -> None:
    repo = DocumentRepository(db_session)
    me = make_user(db_session, "me@example.com")
    other = make_user(db_session, "other@example.com")
    mine = repo.add(me.id, "mine", "upload", "h-mine")
    theirs = repo.add(other.id, "theirs", "upload", "h-theirs")
    shared = repo.add(other.id, "shared", "openfda", "h-shared", is_shared=True)
    visible = {d.id for d in repo.list_visible(me.id)}
    assert visible == {mine.id, shared.id}
    assert theirs.id not in visible
