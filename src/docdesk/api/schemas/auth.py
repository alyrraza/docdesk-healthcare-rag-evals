"""Request and response models for the auth routes."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegisterRequest(BaseModel):
    """What a new user sends. Unknown fields, such as a role, are ignored."""

    model_config = ConfigDict(extra="ignore")

    email: str = Field(max_length=320)
    # The upper bound stops very long inputs from making the slow hash expensive to compute.
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def email_must_look_like_an_address(cls, value: str) -> str:
        """Reject obvious typos early; real ownership is not verified in this project."""
        if not EMAIL_PATTERN.match(value.strip()):
            raise ValueError("not an email address")
        return value.strip()


class UserOut(BaseModel):
    """What the API reveals about a user: never the hash."""

    id: str
    email: str
    role: str


class LoginRequest(BaseModel):
    """Credentials posted to /auth/login."""

    email: str = Field(max_length=320)
    password: str = Field(min_length=1, max_length=128)


class TokenOut(BaseModel):
    """The login result."""

    access_token: str
    token_type: str = "bearer"
