"""Report numbers (T095): intervals per category, label counts, judge failures, paired runs."""

from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from docdesk.db.models.evals import EvalRunRow
from docdesk.evals import run_store
from docdesk.evals.metrics.abstention import AbstentionCounts, count_cells
from docdesk.evals.report_usage import ModelUsage, usage_from_records
from docdesk.evals.stats import (
    DEFAULT_RESAMPLES,
    DEFAULT_SEED,
    Interval,
    bootstrap_ci,
)

# Documented in evals.md: 2000 bootstrap resamples with seed 0, so a report can be rebuilt exactly.
RESAMPLES = DEFAULT_RESAMPLES
SEED = DEFAULT_SEED
CATEGORY_ORDER = (
    "single_fact", "multi_chunk", "structured", "mixed", "unanswerable", "adversarial",
)
METRICS = (
    "pass_rate", "recall", "hit", "mrr", "context_precision",
    "citation_precision", "citation_recall", "faithfulness", "correctness",
)
# Judge statuses that are not failures. Anything else (parse_failed or an error name) is counted.
JUDGE_OK = (None, "scored", "no_claims", "skipped", "decided_by_code")


@dataclass(frozen=True)
class ResultRecord:
    """One stored eval_results row, without the database."""

    item_id: str
    metrics: dict[str, Any]
    failure_label: str | None
    # The stored judge labels and chunk ids, read by the worst items section.
    trace: dict[str, Any] = field(default_factory=dict)
    # Per call token entries of this run (T098b); None for rows stored before that existed.
    usage: list[dict[str, Any]] | None = None


@dataclass(frozen=True)
class RunData:
    """A run and its rows."""

    run_id: str
    config_id: str
    split: str
    mode: str
    records: list[ResultRecord]


@dataclass(frozen=True)
class MetricCell:
    """A mean with its interval, and how many items had a value (None values are left out)."""

    n: int
    interval: Interval | None


@dataclass
class Category:
    """One row group of the report."""

    name: str
    n: int
    metrics: dict[str, MetricCell]


@dataclass
class Report:
    """Everything the markdown writer needs, computed once."""

    run: RunData
    categories: list[Category]
    overall: Category
    failure_labels: dict[str, int]
    judge_failures: dict[str, dict[str, int]]
    abstention: AbstentionCounts
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: Decimal = Decimal("0")
    cache_hits: int = 0
    llm_calls: int = 0
    not_run: list[tuple[str, str]] = field(default_factory=list)
    total_ok: int = 0
    # None when the run was stored before per call usage existed (never guessed).
    model_usage: list[ModelUsage] | None = None


def value_of(record: ResultRecord, metric: str) -> float | None:
    """One metric of one item; pass_rate turns the passed flag into 1.0 or 0.0."""
    if metric == "pass_rate":
        passed = record.metrics.get("passed")
        return None if passed is None else float(passed)
    return record.metrics.get(metric)


def cell(records: list[ResultRecord], metric: str) -> MetricCell:
    """Mean and bootstrap interval over items that have the metric; documents resample whole."""
    pairs = [(value_of(r, metric), r.metrics.get("group", r.item_id)) for r in records]
    pairs = [(value, group) for value, group in pairs if value is not None]
    if not pairs:
        return MetricCell(0, None)
    values, groups = [p[0] for p in pairs], [p[1] for p in pairs]
    interval = bootstrap_ci(values, groups=groups, n_resamples=RESAMPLES, seed=SEED)
    return MetricCell(len(values), interval)


def category(name: str, records: list[ResultRecord]) -> Category:
    """All metrics for one group of items."""
    return Category(name, len(records), {m: cell(records, m) for m in METRICS})


def judge_failure_counts(records: list[ResultRecord]) -> dict[str, dict[str, int]]:
    """Per judge: parse failures and judge errors (a provider error), never hidden."""
    result: dict[str, dict[str, int]] = {}
    for judge in ("faithfulness", "correctness"):
        counts: Counter[str] = Counter()
        for record in records:
            status = record.metrics.get(f"{judge}_status")
            if status not in JUDGE_OK:
                counts["parse_failed" if status == "parse_failed" else "judge_error"] += 1
        result[judge] = dict(counts)
    return result


def build_report(run: RunData) -> Report:
    """Aggregate the run. Not run items are listed apart and never counted as failures."""
    ran = [r for r in run.records if r.metrics.get("status") == "ok"]
    names = [n for n in CATEGORY_ORDER if any(r.metrics["type"] == n for r in ran)]
    pairs = [(r.metrics["behavior"], r.metrics["outcome"]) for r in ran if r.metrics["outcome"]]
    return Report(
        run=run,
        categories=[category(n, [r for r in ran if r.metrics["type"] == n]) for n in names],
        overall=category("all", ran),
        failure_labels=dict(Counter(r.failure_label for r in ran if r.failure_label)),
        judge_failures=judge_failure_counts(ran),
        abstention=count_cells(pairs),
        tokens_in=sum(r.metrics.get("tokens_in", 0) for r in ran),
        tokens_out=sum(r.metrics.get("tokens_out", 0) for r in ran),
        cost_usd=sum((Decimal(r.metrics.get("cost_usd", "0")) for r in ran), Decimal("0")),
        cache_hits=sum(r.metrics.get("cache_hits", 0) for r in ran),
        llm_calls=sum(r.metrics.get("llm_calls", 0) for r in ran),
        not_run=[(r.item_id, r.metrics["reason"]) for r in run.records
                 if r.metrics.get("status") == "not_run"],
        total_ok=len(ran),
        model_usage=usage_from_records(run.records),
    )


def load_run_data(session: Session, run_id: uuid.UUID) -> RunData:
    """Read a stored run into plain data."""
    run = session.get(EvalRunRow, run_id)
    if run is None:
        raise LookupError(f"no eval run with id {run_id}")
    records = [ResultRecord(r.item_id, r.metrics, r.failure_label, r.trace, r.usage)
               for r in run_store.results_of(session, run_id)]
    mode = next((r.metrics["mode"] for r in records if "mode" in r.metrics), "full")
    return RunData(str(run.id), run.config_id, run.split, mode, records)
