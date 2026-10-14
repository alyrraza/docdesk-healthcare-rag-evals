"""Reads and writes eval_runs and eval_results, so a stopped run can be found and continued."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from docdesk.core import clock
from docdesk.db.models.evals import EvalResultRow, EvalRunRow
from docdesk.evals.identity import RunIdentityMismatch, differing_keys


def open_run(
    session: Session,
    *,
    config_id: str,
    bundle_id: str | None,
    split: str,
    git_sha: str,
    label: str | None = None,
    identity: dict[str, Any] | None = None,
) -> EvalRunRow:
    """Continue the unfinished run with the same identity, or start a new one.

    A run stored without an identity (legacy) is never continued. An unfinished run of the same
    config whose pins differ is refused, not skipped, so a changed judge cannot mix into it.

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
    )
    wanted = identity or {}
    for candidate in session.execute(unfinished).scalars():
        if candidate.identity is None:
            continue
        wrong = differing_keys(candidate.identity, wanted)
        if not wrong:
            return candidate
        if wrong == ["items"]:
            continue  # another item set is another run, never a continuation
        raise RunIdentityMismatch(
            f"unfinished run {candidate.id} was started with other {', '.join(wrong)}"
        )
    run = EvalRunRow(
        config_id=config_id,
        prompt_bundle_id=bundle_id,
        split=split,
        started_at=clock.utc_now(),
        git_sha=git_sha,
        label=label,
        identity=identity,
    )
    session.add(run)
    session.flush()
    return run


def written_item_ids(session: Session, run_id: uuid.UUID) -> set[str]:
    """Items with a finished result row; a rerun skips exactly these and retries not scored ones."""
    query = select(EvalResultRow.item_id, EvalResultRow.metrics)
    rows = session.execute(query.where(EvalResultRow.run_id == run_id))
    return {item for item, metrics in rows if metrics.get("status") != "not_scored"}


def parse_failed_items(metrics_by_item: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    """Why: a resumed run must report earlier parse failures too, so they come from stored rows."""
    def failed(judge: str) -> list[str]:
        status = f"{judge}_status"
        return sorted(i for i, m in metrics_by_item.items() if m.get(status) == "parse_failed")

    return {judge: failed(judge) for judge in ("faithfulness", "correctness")}


def add_result(
    session: Session,
    run_id: uuid.UUID,
    item_id: str,
    metrics: dict[str, Any],
    failure_label: str | None,
    trace: dict[str, Any],
    usage: list[dict[str, Any]] | None = None,
    latency: dict[str, Any] | None = None,
) -> None:
    """Write one item's row at once; a retry replaces the earlier not scored row of that item."""
    session.merge(
        EvalResultRow(
            run_id=run_id,
            item_id=item_id,
            metrics=metrics,
            failure_label=failure_label,
            trace=trace,
            usage=usage,
            latency=latency,
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
