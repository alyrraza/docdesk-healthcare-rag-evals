"""Create and verify the signed login token (AC-AUTH-02)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta

import jwt

from docdesk.core import clock
from docdesk.core.config import Settings
from docdesk.db.repositories.users import ALLOWED_ROLES, User

ALGORITHM = "HS256"


class TokenError(Exception):
    """The token is missing, malformed, expired, forged or has unusable claims."""


@dataclass(frozen=True)
class TokenClaims:
    """The two facts a request needs from a verified token."""

    user_id: uuid.UUID
    role: str


def create_token(user: User, settings: Settings) -> str:
    """Issue a short lived token holding only who (sub), what (role) and until when (exp)."""
    expires = clock.utc_now() + timedelta(minutes=settings.jwt_lifetime_minutes)
    claims = {"sub": str(user.id), "role": user.role, "exp": expires}
    return jwt.encode(claims, settings.jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str, settings: Settings) -> TokenClaims:
    """Verify signature and expiry, then check the claims, turning every failure into TokenError."""
    try:
        raw = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "sub", "role"]},
        )
        user_id = uuid.UUID(raw["sub"])
    except (jwt.PyJWTError, ValueError, TypeError) as error:
        raise TokenError("invalid token") from error
    role = raw["role"]
    if role not in ALLOWED_ROLES:
        raise TokenError("unknown role in token")
    return TokenClaims(user_id=user_id, role=role)
