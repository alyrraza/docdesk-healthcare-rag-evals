"""Tests for db/session.py against the real test database."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from docdesk.db import session as session_module
from docdesk.db.session import make_engine, make_session_factory

pytestmark = pytest.mark.integration


def test_session_runs_a_query(test_database_url: str) -> None:
    factory = make_session_factory(make_engine(test_database_url))
    with factory() as session:
        assert session.execute(text("SELECT 1")).scalar_one() == 1


def test_get_session_closes_the_connection_after_the_request(
    test_database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = make_engine(test_database_url)
    factory = make_session_factory(engine)
    monkeypatch.setattr(session_module, "default_session_factory", lambda: factory)
    request = session_module.get_session()
    session = next(request)
    session.execute(text("SELECT 1"))
    assert engine.pool.checkedout() == 1
    request.close()
    assert engine.pool.checkedout() == 0


def test_get_session_closes_even_when_the_request_fails(
    test_database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = make_engine(test_database_url)
    factory = make_session_factory(engine)
    monkeypatch.setattr(session_module, "default_session_factory", lambda: factory)
    request = session_module.get_session()
    session = next(request)
    session.execute(text("SELECT 1"))
    with pytest.raises(RuntimeError):
        request.throw(RuntimeError("handler failed"))
    assert engine.pool.checkedout() == 0
