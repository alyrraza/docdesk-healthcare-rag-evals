"""Auth use cases that routers call, so routers stay thin."""

from __future__ import annotations

from sqlalchemy.orm import Session

from docdesk.auth.passwords import hash_password
from docdesk.auth.roles import Role
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
