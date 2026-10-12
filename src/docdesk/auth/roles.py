"""The roles a user can hold."""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    """Two roles are enough: admins manage prompts and see every trace."""

    USER = "user"
    ADMIN = "admin"
