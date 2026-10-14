"""Paired comparison of two runs (T095): the same items, candidate minus baseline."""

from __future__ import annotations

from dataclasses import dataclass, field

from docdesk.evals.identity import identity_warnings
from docdesk.evals.report_data import RESAMPLES, SEED, ResultRecord, RunData, value_of
from docdesk.evals.stats import PairedResult, paired_comparison

COMPARED = ("pass_rate", "recall", "mrr", "faithfulness", "correctness")


@dataclass(frozen=True)
class ComparisonRow:
    """One metric compared over the items both runs have a value for."""

    metric: str
    n_paired: int
    paired: PairedResult | None


@dataclass(frozen=True)
class Comparison:
    """Candidate minus baseline, paired by item id."""

    baseline_id: str
    candidate_id: str
    shared: int
    only_baseline: list[str]
    only_candidate: list[str]
    rows: list[ComparisonRow]
    # Why the two runs may not be comparable (split, mode, judge, corpus); shown above the table.
    warnings: list[str] = field(default_factory=list)
    # Facts that are not differences, such as a legacy identity read from row traces.
    notes: list[str] = field(default_factory=list)


def compare_runs(baseline: RunData, candidate: RunData) -> Comparison:
    """Paired comparison on the items both runs ran; the others are named, not guessed."""
    def ran(data: RunData) -> dict[str, ResultRecord]:
        return {r.item_id: r for r in data.records if r.metrics.get("status") == "ok"}

    base, cand = ran(baseline), ran(candidate)
    shared = sorted(base.keys() & cand.keys())
    rows = []
    for metric in COMPARED:
        both = [i for i in shared
                if value_of(base[i], metric) is not None and value_of(cand[i], metric) is not None]
        if not both:
            rows.append(ComparisonRow(metric, 0, None))
            continue
        paired = paired_comparison(
            [value_of(base[i], metric) for i in both],
            [value_of(cand[i], metric) for i in both],
            groups=[base[i].metrics.get("group", i) for i in both],
            n_resamples=RESAMPLES, seed=SEED,
        )
        rows.append(ComparisonRow(metric, len(both), paired))
    warnings = identity_warnings(baseline.identity, candidate.identity)
    if baseline.split != candidate.split:
        warnings.insert(0, f"split differs: {baseline.split} against {candidate.split}")
    if baseline.mode != candidate.mode:
        warnings.insert(0, f"mode differs: {baseline.mode} against {candidate.mode}")
    notes = [f"run {data.run_id} has a legacy identity, read from its row traces"
             for data in (baseline, candidate) if (data.identity or {}).get("legacy")]
    return Comparison(
        baseline.run_id, candidate.run_id, len(shared),
        sorted(base.keys() - cand.keys()), sorted(cand.keys() - base.keys()), rows,
        warnings, notes,
    )
