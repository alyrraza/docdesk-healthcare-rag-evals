"""Auth use cases that routers call, so routers stay thin."""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy.orm import Session

from docdesk.auth.jwt import create_token
from docdesk.auth.passwords import hash_password, verify_password
from docdesk.auth.roles import Role
from docdesk.core.config import Settings
from docdesk.core.errors import AppError
from docdesk.db.repositories.users import DuplicateEmailError, User, UserRepository


def register_user(session: Session, email: str, password: str) -> User:
    """Create a normal user; the role is fixed here so a caller can never pick admin."""
    repo = UserRepository(session)
    try:
        user = repo.add(email, hash_password(password), Role.USER.value)
    except DuplicateEmailError as error:
        message = "Email already registered"
        raise AppError(code="email_taken", message=message, status=409) from error
    session.commit()
    return user


@lru_cache
def _decoy_hash() -> str:
    """A valid hash of a throwaway password, used to spend the same time for unknown emails."""
    return hash_password("decoy-password-never-matches")


def login_user(session: Session, settings: Settings, email: str, password: str) -> str:
    """Return a token for valid credentials; every failure is the same 401 (AC-AUTH-02)."""
    user = UserRepository(session).get_by_email(email)
    # Always run one hash check so response time does not reveal whether the email exists.
    stored = user.password_hash if user else _decoy_hash()
    if not verify_password(password, stored) or user is None:
        raise AppError(code="invalid_credentials", message="Invalid email or password", status=401)
    return create_token(user, settings)
