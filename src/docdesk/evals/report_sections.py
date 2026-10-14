"""Report sections for answerable items (T098a): strict pass, stages, label table, worst five."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from docdesk.evals.labeler import LABEL_ORDER
from docdesk.evals.passing import scores_pass
from docdesk.evals.report_data import MetricCell, ResultRecord, cell

STAGES = ("retrieval", "packing", "generation", "pass")
RETRIEVAL_LABELS = ("retrieval_miss", "ranking_miss")
PACKING_LABELS = ("context_overflow",)
PASSED_ROW = "no label (passed)"
OUTCOMES = ("answered", "abstained", "refused", "error")
WORST_COUNT = 5


@dataclass(frozen=True)
class StrictPass:
    """Answerable items that scored 1.0 on both judges, with an interval for the rate."""

    n: int
    passed: int
    cell: MetricCell


@dataclass(frozen=True)
class StageSplit:
    """Where answerable items failed, and the labels behind each stage."""

    n: int
    counts: dict[str, int]
    labels: dict[str, dict[str, int]]


@dataclass(frozen=True)
class WorstItem:
    """One of the lowest scoring answered items, with a line of counts and no opinion."""

    item_id: str
    item_type: str
    label: str | None
    line: str


def answerable_records(records: list[ResultRecord]) -> list[ResultRecord]:
    """Why: the harness pass flag counts correct abstains, so answerable items are split out."""
    return [r for r in records
            if r.metrics.get("status") == "ok" and r.metrics.get("behavior") == "answer"]


def is_strict_pass(record: ResultRecord) -> bool:
    """The shared pass rule on stored scores; a missing score (abstain, judge failure) fails."""
    metrics = record.metrics
    return scores_pass(
        metrics.get("faithfulness"), metrics.get("correctness"), metrics.get("contradicted", 0)
    )


def strict_pass_rate(records: list[ResultRecord]) -> StrictPass:
    """The strict pass rate over answerable items, as a count and a bootstrap interval."""
    items = answerable_records(records)
    flags = [ResultRecord(r.item_id, {"strict": float(is_strict_pass(r)),
                                      "group": r.metrics.get("group", r.item_id)}, None)
             for r in items]
    return StrictPass(len(items), sum(is_strict_pass(r) for r in items), cell(flags, "strict"))


def stage_of(label: str | None) -> str:
    """Which stage a label blames: retrieval, the packer, or the model."""
    if label is None:
        return "pass"
    if label in RETRIEVAL_LABELS:
        return "retrieval"
    return "packing" if label in PACKING_LABELS else "generation"


def stage_split(records: list[ResultRecord]) -> StageSplit:
    """Count answerable items by the stage that failed them, so a fix is aimed at the right one."""
    items = answerable_records(records)
    labels: dict[str, Counter[str]] = {stage: Counter() for stage in STAGES}
    for item in items:
        if item.failure_label:
            labels[stage_of(item.failure_label)][item.failure_label] += 1
    counts = Counter(stage_of(item.failure_label) for item in items)
    return StageSplit(
        len(items),
        {stage: counts[stage] for stage in STAGES},
        {stage: dict(sorted(found.items())) for stage, found in labels.items()},
    )


def label_by_outcome(records: list[ResultRecord]) -> dict[str, dict[str, int]]:
    """Every run item by failure label and outcome, so wrong abstains show under their label."""
    table: dict[str, Counter[str]] = {}
    for r in records:
        if r.metrics.get("status") == "ok":
            row = r.failure_label or PASSED_ROW
            table.setdefault(row, Counter())[r.metrics["outcome"]] += 1
    order = [*LABEL_ORDER, PASSED_ROW]
    names = sorted(table, key=lambda n: order.index(n) if n in order else len(order))
    return {name: {o: table[name][o] for o in OUTCOMES if table[name][o]} for name in names}


def lowest_score(record: ResultRecord) -> float | None:
    """The lower of the two judge scores, or None when neither judge gave one."""
    scores = [s for s in (record.metrics.get("faithfulness"), record.metrics.get("correctness"))
              if s is not None]
    return min(scores) if scores else None


def fact_line(record: ResultRecord) -> str:
    """Counts from the stored judge labels, the stored recall and the chunk ids; no opinion."""
    faith = [x["label"] for x in record.trace.get("faithfulness_labels", [])]
    correct = Counter(x["label"] for x in record.trace.get("correctness_labels", []))
    score = record.metrics.get("faithfulness")
    parts = [
        f"correctness {_score(record.metrics.get('correctness'))} "
        f"({correct['covered']} covered, {correct['missing']} missing, "
        f"{correct['contradicted']} contradicted)",
        f"faithfulness {_score(score)} "
        f"({faith.count('supported')} of {len(faith)} claims supported)",
        f"recall@k {_score(record.metrics.get('recall'))}",
        f"{len(record.trace.get('used_ids', []))} chunks in the prompt, "
        f"{len(record.trace.get('cited_ids', []))} cited",
    ]
    return ", ".join(parts) + "."


def _score(value: float | None) -> str:
    """Two decimals, or n/a for a judge that gave no score."""
    return "n/a" if value is None else f"{value:.2f}"


def worst_answered(records: list[ResultRecord], count: int = WORST_COUNT) -> list[WorstItem]:
    """The answered items with the lowest judge score; ties go to the lower item id."""
    scored = [(lowest_score(r), r) for r in records
              if r.metrics.get("status") == "ok" and r.metrics.get("outcome") == "answered"]
    ranked = sorted(((s, r) for s, r in scored if s is not None),
                    key=lambda pair: (pair[0], pair[1].item_id))
    return [WorstItem(r.item_id, r.metrics["type"], r.failure_label, fact_line(r))
            for _, r in ranked[:count]]
