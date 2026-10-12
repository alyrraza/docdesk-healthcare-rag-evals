"""Tests for the users table and its repository."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from docdesk.db.repositories.users import DuplicateEmailError, UserRepository

pytestmark = pytest.mark.integration


def test_add_then_find_by_email(db_session: Session) -> None:
    repo = UserRepository(db_session)
    created = repo.add("Ana@Example.com", "hash-1", "user")
    found = repo.get_by_email("ana@example.com")
    assert found is not None
    assert found.id == created.id
    assert found.email == "ana@example.com"
    assert found.password_hash == "hash-1"
    assert found.role == "user"
    assert found.created_at.tzinfo is not None


def test_find_by_id(db_session: Session) -> None:
    repo = UserRepository(db_session)
    created = repo.add("b@example.com", "h", "admin")
    assert repo.get_by_id(created.id) == created


def test_unknown_user_returns_none(db_session: Session) -> None:
    assert UserRepository(db_session).get_by_email("nobody@example.com") is None


def test_duplicate_email_is_rejected_case_insensitively(db_session: Session) -> None:
    repo = UserRepository(db_session)
    repo.add("c@example.com", "h", "user")
    with pytest.raises(DuplicateEmailError):
        repo.add("C@EXAMPLE.COM", "h", "user")


def test_unknown_role_is_rejected(db_session: Session) -> None:
    with pytest.raises(ValueError):
        UserRepository(db_session).add("d@example.com", "h", "superuser")
