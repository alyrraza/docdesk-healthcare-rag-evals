"""Password hashing with argon2id. Plain passwords are never stored or logged."""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Store only a slow, salted hash so a database leak does not reveal passwords."""
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Check a login attempt; any mismatch or bad hash is a plain False, never an exception."""
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False
