"""Declarative base shared by every table so Alembic sees one metadata object."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Parent class of all table models."""
