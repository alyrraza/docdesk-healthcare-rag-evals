"""Tests for seeding the first admin user."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from docdesk.auth.passwords import verify_password
from docdesk.auth.seed import ensure_admin
from docdesk.db.repositories.users import UserRepository

pytestmark = pytest.mark.integration

PASSWORD = "a-strong-admin-password"


def test_creates_an_admin_with_a_hashed_password(db_session: Session) -> None:
    user, created = ensure_admin(db_session, "Admin@Example.com", PASSWORD)
    assert created is True
    assert user.role == "admin"
    assert user.email == "admin@example.com"
    assert user.password_hash != PASSWORD
    assert verify_password(PASSWORD, user.password_hash)


def test_running_twice_does_not_create_a_second_admin(db_session: Session) -> None:
    first, _ = ensure_admin(db_session, "admin@example.com", PASSWORD)
    second, created = ensure_admin(db_session, "admin@example.com", "a-different-password-1")
    assert created is False
    assert second.id == first.id
    # An existing admin keeps their password; seeding is not a password reset.
    assert verify_password(PASSWORD, second.password_hash)


def test_refuses_to_promote_an_existing_normal_user(db_session: Session) -> None:
    UserRepository(db_session).add("person@example.com", "hash", "user")
    with pytest.raises(ValueError, match="not an admin"):
        ensure_admin(db_session, "person@example.com", PASSWORD)


@pytest.mark.parametrize("password", ["", "short", "x" * 11])
def test_refuses_a_weak_admin_password(db_session: Session, password: str) -> None:
    with pytest.raises(ValueError, match="at least 12"):
        ensure_admin(db_session, "admin@example.com", password)
