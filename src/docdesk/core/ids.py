"""Identifier helpers."""

from __future__ import annotations

from uuid import uuid4


def new_trace_id() -> str:
    """Give each request one random id so logs and stored traces can be joined."""
    return uuid4().hex
