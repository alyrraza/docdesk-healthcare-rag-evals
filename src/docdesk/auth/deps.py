"""FastAPI dependencies that protect routes."""

from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from docdesk.auth.jwt import TokenClaims, TokenError, decode_token
from docdesk.core.config import Settings, get_settings
from docdesk.core.errors import AppError

# auto_error=False lets us answer in our own error envelope instead of FastAPI's default body.
_bearer = HTTPBearer(auto_error=False)


def unauthorized(message: str) -> AppError:
    """Build the one 401 error every failed login check uses."""
    return AppError(code="unauthorized", message=message, status=401)


def require_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> TokenClaims:
    """Reject the request unless it carries a valid bearer token (AC-AUTH-03)."""
    if credentials is None:
        raise unauthorized("Missing bearer token")
    try:
        return decode_token(credentials.credentials, settings)
    except TokenError as error:
        raise unauthorized("Invalid or expired token") from error
