"""Numbers for a retrieval only run (T097): recall, hit, MRR, labels, top-1 scores, worst items.

Pure functions over ranked chunks, so the numbers can be tested without a database or a model.
Intervals reuse the report code: 2000 bootstrap resamples, seed 0, items of one document together.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Any

from docdesk.evals import labeler
from docdesk.evals.metrics import retrieval as rm
from docdesk.evals.outcome import outcome_cell
from docdesk.evals.report_data import RESAMPLES, SEED, ResultRecord, cell

KS = (1, 3, 5)
TEXT_LIMIT = 300
# The cell of an answerable item that was not answered, so the retrieval label rules apply.
FAILED_CELL = outcome_cell("answer", "abstained")


@dataclass(frozen=True)
class Hit:
    """One ranked chunk: its id, document title, dense score and text."""

    chunk_id: str
    title: str
    score: float
    text: str


@dataclass(frozen=True)
class ItemRow:
    """One dev item and what B0 retrieved for it (all top_n candidates, best first)."""

    id: str
    type: str
    behavior: str
    question: str
    gold_sets: list[frozenset[str]]
    entry_labels: list[str]
    ranked: list[Hit]
    group: str


@dataclass(frozen=True)
class Worst:
    """An answerable item with low recall: what it missed and where the missed gold was found."""

    row: ItemRow
    missed: list[str]
    found_at: dict[str, int | None]


def ids_of(row: ItemRow) -> list[str]:
    """Why: the metric functions take plain ids, and the order is the retrieval rank."""
    return [hit.chunk_id for hit in row.ranked]


def metrics_of(row: ItemRow, top_k: int) -> dict[str, Any]:
    """Every retrieval number of one answerable item, as the report interval code reads it."""
    ids, gold = ids_of(row), row.gold_sets
    values: dict[str, Any] = {f"recall@{k}": rm.recall_at_k(ids, gold, k) for k in KS}
    values[f"hit@{top_k}"] = rm.hit_at_k(ids, gold, top_k)
    values["mrr"] = rm.reciprocal_rank(ids, gold, top_k)
    if len(gold) > 1:
        values[f"all_gold@{top_k}"] = float(values[f"recall@{top_k}"] == 1.0)
    return {**values, "group": row.group}


def interval_cell(records: list[ResultRecord], metric: str) -> dict[str, Any] | None:
    """Mean and 95 percent interval of one metric, or None when no item has it."""
    found = cell(records, metric)
    if found.interval is None:
        return None
    interval = found.interval
    return {"n": found.n, "mean": interval.estimate, "low": interval.low, "high": interval.high}


def label_of(row: ItemRow, top_k: int) -> str | None:
    """retrieval_miss when gold is not a candidate, ranking_miss when it fell outside top_k."""
    ids = ids_of(row)
    item = labeler.LabelInput(
        behavior="answer", outcome="abstained", retrieval_ran=True, packed=False,
        gold_sets=row.gold_sets, candidate_ids=ids, retrieved_ids=ids[:top_k], used_ids=[],
    )
    if labeler.retrieval_miss(item, FAILED_CELL):
        return "retrieval_miss"
    return "ranking_miss" if labeler.ranking_miss(item, FAILED_CELL) else None


def score_spread(rows: list[ItemRow]) -> dict[str, dict[str, Any]]:
    """Top-1 dense score min, median and max per category, for every item that got a result."""
    spread: dict[str, dict[str, Any]] = {}
    for kind in dict.fromkeys(row.type for row in rows):
        tops = [row.ranked[0].score for row in rows if row.type == kind and row.ranked]
        if tops:
            spread[kind] = {"n": len(tops), "min": min(tops), "median": median(tops),
                            "max": max(tops)}
    return spread


def summarize(rows: list[ItemRow], top_k: int) -> dict[str, Any]:
    """All numbers of the run as plain data, ready for json and for the markdown writer."""
    answerable = [row for row in rows if row.gold_sets]
    records = {row.id: ResultRecord(row.id, metrics_of(row, top_k), None) for row in answerable}
    groups = {
        "single_fact": [r for r in answerable if r.type == "single_fact"],
        "multi_chunk": [r for r in answerable if r.type == "multi_chunk"],
        "all": answerable,
    }
    categories: dict[str, Any] = {}
    for name, members in groups.items():
        recs = [records[row.id] for row in members]
        entry: dict[str, Any] = {"n": len(members)}
        wanted = [*(f"recall@{k}" for k in KS), f"hit@{top_k}", "mrr"]
        if name == "multi_chunk":
            wanted.append(f"all_gold@{top_k}")
        for metric in wanted:
            if stats := interval_cell(recs, metric):
                entry[metric] = stats
        categories[name] = entry
    labels = [label for row in answerable if (label := label_of(row, top_k))]
    return {
        "top_k": top_k, "resamples": RESAMPLES, "seed": SEED, "categories": categories,
        "failure_labels": {n: labels.count(n) for n in dict.fromkeys(labels)},
        "top1_scores": score_spread(rows),
    }


def worst_items(rows: list[ItemRow], top_k: int, count: int = 5) -> list[Worst]:
    """The answerable items with the lowest recall@top_k (ties: lower MRR, then id)."""
    answerable = [row for row in rows if row.gold_sets]

    def key(row: ItemRow) -> tuple[float, float, str]:
        values = metrics_of(row, top_k)
        return (values[f"recall@{top_k}"], values["mrr"], row.id)

    result = []
    for row in sorted(answerable, key=key)[:count]:
        ids, missed, found = ids_of(row), [], {}
        for gold, label in zip(row.gold_sets, row.entry_labels, strict=True):
            if not gold & set(ids[:top_k]):
                missed.append(label)
                ranks = [n for n, chunk_id in enumerate(ids, start=1) if chunk_id in gold]
                found[label] = ranks[0] if ranks else None
        result.append(Worst(row, missed, found))
    return result
