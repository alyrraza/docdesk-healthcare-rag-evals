"""Tests for the eval_runs and eval_results tables."""

from __future__ import annotations

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from docdesk.core import clock
from docdesk.db.models.evals import EvalResultRow, EvalRunRow

pytestmark = pytest.mark.integration


def make_run() -> EvalRunRow:
    return EvalRunRow(
        config_id="b0",
        prompt_bundle_id="bundle-1",
        split="dev",
        started_at=clock.utc_now(),
        git_sha="abc1234",
    )


def make_result(run_id, item_id: str = "item-1") -> EvalResultRow:
    return EvalResultRow(
        run_id=run_id,
        item_id=item_id,
        metrics={"recall_at_5": 1.0, "faithfulness": 0.8},
        failure_label="retrieval_miss",
        trace={"answer": "text"},
    )


def test_run_and_results_round_trip(db_session: Session) -> None:
    run = make_run()
    db_session.add(run)
    db_session.flush()
    db_session.add(make_result(run.id))
    db_session.flush()
    stored = db_session.execute(select(EvalResultRow)).scalar_one()
    assert stored.metrics["faithfulness"] == 0.8
    assert stored.failure_label == "retrieval_miss"
    assert db_session.get(EvalRunRow, run.id).finished_at is None


def test_each_item_appears_once_per_run(db_session: Session) -> None:
    run = make_run()
    db_session.add(run)
    db_session.flush()
    db_session.add(make_result(run.id))
    db_session.flush()
    db_session.expunge_all()
    db_session.add(make_result(run.id))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_same_item_can_appear_in_different_runs(db_session: Session) -> None:
    first, second = make_run(), make_run()
    db_session.add_all([first, second])
    db_session.flush()
    db_session.add_all([make_result(first.id), make_result(second.id)])
    db_session.flush()


def test_deleting_a_run_deletes_its_results(db_session: Session) -> None:
    run = make_run()
    db_session.add(run)
    db_session.flush()
    db_session.add(make_result(run.id))
    db_session.flush()
    db_session.execute(text("DELETE FROM eval_runs WHERE id = :id"), {"id": run.id})
    assert db_session.execute(text("SELECT count(*) FROM eval_results")).scalar_one() == 0


def test_unknown_split_is_rejected(db_session: Session) -> None:
    run = make_run()
    run.split = "validation"
    db_session.add(run)
    with pytest.raises(IntegrityError):
        db_session.flush()
