"""Reads and writes eval_runs and eval_results, so a stopped run can be found and continued."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from docdesk.core import clock
from docdesk.db.models.evals import EvalResultRow, EvalRunRow


def open_run(
    session: Session,
    *,
    config_id: str,
    bundle_id: str | None,
    split: str,
    git_sha: str,
    label: str | None = None,
) -> EvalRunRow:
    """Continue the newest unfinished run of the same setup, or start a new one.

    A retrieval only run has no prompt bundle (None), so it never continues a full run.
    The label is stored only on a new run; a continued run keeps the label it started with.
    """
    same_bundle = (
        EvalRunRow.prompt_bundle_id.is_(None)
        if bundle_id is None
        else EvalRunRow.prompt_bundle_id == bundle_id
    )
    unfinished = (
        select(EvalRunRow)
        .where(
            EvalRunRow.config_id == config_id,
            same_bundle,
            EvalRunRow.split == split,
            EvalRunRow.finished_at.is_(None),
        )
        .order_by(EvalRunRow.started_at.desc())
        .limit(1)
    )
    found = session.execute(unfinished).scalar_one_or_none()
    if found is not None:
        return found
    run = EvalRunRow(
        config_id=config_id,
        prompt_bundle_id=bundle_id,
        split=split,
        started_at=clock.utc_now(),
        git_sha=git_sha,
        label=label,
    )
    session.add(run)
    session.flush()
    return run


def written_item_ids(session: Session, run_id: uuid.UUID) -> set[str]:
    """Items that already have a result row; a rerun skips exactly these."""
    rows = session.execute(select(EvalResultRow.item_id).where(EvalResultRow.run_id == run_id))
    return set(rows.scalars())


def add_result(
    session: Session,
    run_id: uuid.UUID,
    item_id: str,
    metrics: dict[str, Any],
    failure_label: str | None,
    trace: dict[str, Any],
    usage: list[dict[str, Any]] | None = None,
) -> None:
    """Write one item's row at once, so an interruption never loses a finished item."""
    session.add(
        EvalResultRow(
            run_id=run_id,
            item_id=item_id,
            metrics=metrics,
            failure_label=failure_label,
            trace=trace,
            usage=usage,
        )
    )
    session.flush()


def finish_run(session: Session, run: EvalRunRow) -> None:
    """Stamp the end time; an unfinished run is the one a rerun continues."""
    run.finished_at = clock.utc_now()
    session.flush()


def results_of(session: Session, run_id: uuid.UUID) -> list[EvalResultRow]:
    """Every result row of a run in item id order, for the report."""
    query = select(EvalResultRow).where(EvalResultRow.run_id == run_id)
    return list(session.execute(query.order_by(EvalResultRow.item_id)).scalars())


def latest_run_id(session: Session) -> uuid.UUID:
    """The newest run, for a report asked without an id."""
    newest = session.execute(
        select(EvalRunRow.id).order_by(EvalRunRow.started_at.desc()).limit(1)
    ).scalar_one_or_none()
    if newest is None:
        raise LookupError("there are no eval runs yet")
    return newest
