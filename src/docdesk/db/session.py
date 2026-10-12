"""Engine and per-request database session."""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from docdesk.core.config import get_settings


def make_engine(url: str) -> Engine:
    """Build an engine that tests can point at the test database."""
    return create_engine(url, pool_pre_ping=True)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create sessions that never commit by themselves, so writes are explicit."""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@lru_cache
def default_session_factory() -> sessionmaker[Session]:
    """Build the app's engine once from settings and reuse its connection pool."""
    return make_session_factory(make_engine(get_settings().database_url))


def get_session() -> Iterator[Session]:
    """Open one session per request and always close it so connections return to the pool."""
    with default_session_factory()() as session:
        yield session
