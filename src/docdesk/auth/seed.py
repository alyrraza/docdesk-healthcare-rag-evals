"""Create the first admin account. The API cannot create admins, so this is how one exists."""

from __future__ import annotations

from sqlalchemy.orm import Session

from docdesk.auth.passwords import hash_password
from docdesk.auth.roles import Role
from docdesk.db.repositories.users import User, UserRepository

MIN_ADMIN_PASSWORD_LENGTH = 12


def ensure_admin(session: Session, email: str, password: str) -> tuple[User, bool]:
    """Make sure one admin with this email exists; return the user and whether it was created."""
    if len(password) < MIN_ADMIN_PASSWORD_LENGTH:
        message = f"admin password must have at least {MIN_ADMIN_PASSWORD_LENGTH} characters"
        raise ValueError(message)
    repo = UserRepository(session)
    existing = repo.get_by_email(email)
    if existing is None:
        return repo.add(email, hash_password(password), Role.ADMIN.value), True
    if existing.role != Role.ADMIN:
        raise ValueError(f"{existing.email} exists but is not an admin; refusing to promote it")
    return existing, False
