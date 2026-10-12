"""Tests for the query_traces table (AC-OBS-01 stores one row per request)."""

from __future__ import annotations

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from docdesk.core import clock
from docdesk.db.models.traces import QueryTraceRow
from docdesk.db.repositories.users import UserRepository

pytestmark = pytest.mark.integration


def make_trace(trace_id: str = "a" * 32, user_id=None) -> QueryTraceRow:
    return QueryTraceRow(
        trace_id=trace_id,
        user_id=user_id,
        created_at=clock.utc_now(),
        route="documents",
        question_hash="q-hash",
        config_id="cfg-1",
        prompt_bundle_id="bundle-1",
        retrieved=[{"chunk_id": "c1", "score": 0.9}],
        used_ids=["c1"],
        dropped_ids=[],
        stage_ms={"embed": 12.5, "vector_search": 3.1, "total": 900.0},
        tokens={"in": 800, "out": 120},
        guardrails={"input": "ok"},
        validation={"schema": True, "citations": True},
        total_ms=900.0,
    )


def test_ac_obs_01_trace_round_trips_with_json_fields(db_session: Session) -> None:
    db_session.add(make_trace())
    db_session.flush()
    stored = db_session.execute(select(QueryTraceRow)).scalar_one()
    assert stored.retrieved == [{"chunk_id": "c1", "score": 0.9}]
    assert stored.stage_ms["embed"] == 12.5
    assert stored.validation == {"schema": True, "citations": True}


def test_defaults_describe_a_plain_successful_request(db_session: Session) -> None:
    db_session.add(make_trace())
    db_session.flush()
    stored = db_session.execute(select(QueryTraceRow)).scalar_one()
    assert stored.cache_hit is False
    assert stored.abstained is False
    assert stored.retry_used is False
    assert stored.error_code is None
    assert stored.cost_usd is None
    assert stored.question_text is None


def test_one_row_per_trace_id(db_session: Session) -> None:
    db_session.add(make_trace())
    db_session.flush()
    db_session.expunge_all()
    db_session.add(make_trace())
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_deleting_a_user_keeps_their_traces(db_session: Session) -> None:
    user = UserRepository(db_session).add("traced@example.com", "hash", "user")
    db_session.add(make_trace(user_id=user.id))
    db_session.flush()
    db_session.execute(text("DELETE FROM users WHERE id = :id"), {"id": user.id})
    db_session.expire_all()
    assert db_session.execute(select(QueryTraceRow)).scalar_one().user_id is None


def test_traces_are_indexed_by_user_and_time(db_session: Session) -> None:
    definitions = " ".join(
        db_session.execute(
            text("SELECT indexdef FROM pg_indexes WHERE tablename = 'query_traces'")
        ).scalars()
    )
    assert "user_id" in definitions
    assert "created_at" in definitions
