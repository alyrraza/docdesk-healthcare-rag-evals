"""Reads and writes for the users table."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from docdesk.core import clock
from docdesk.db.models.users import UserRow

ALLOWED_ROLES = frozenset({"user", "admin"})


class DuplicateEmailError(Exception):
    """Raised when an email is already registered, so callers can answer 409."""


@dataclass(frozen=True)
class User:
    """A user as plain data, so callers never hold a database object."""

    id: uuid.UUID
    email: str
    password_hash: str
    role: str
    created_at: datetime


def to_user(row: UserRow) -> User:
    """Convert a table row to the dataclass the rest of the app uses."""
    return User(row.id, row.email, row.password_hash, row.role, row.created_at)


class UserRepository:
    """All user queries live here and are parameterized by SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, email: str, password_hash: str, role: str) -> User:
        """Insert a user; emails are stored lowercase so lookups are case-insensitive."""
        if role not in ALLOWED_ROLES:
            raise ValueError(f"unknown role: {role}")
        row = UserRow(
            email=email.strip().lower(),
            password_hash=password_hash,
            role=role,
            created_at=clock.utc_now(),
        )
        try:
            with self._session.begin_nested():
                self._session.add(row)
        except IntegrityError as error:
            raise DuplicateEmailError(row.email) from error
        return to_user(row)

    def get_by_email(self, email: str) -> User | None:
        """Find a user for login; None means no such account."""
        query = select(UserRow).where(UserRow.email == email.strip().lower())
        row = self._session.execute(query).scalar_one_or_none()
        return to_user(row) if row else None

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Find the user named by a token's subject claim."""
        row = self._session.get(UserRow, user_id)
        return to_user(row) if row else None
