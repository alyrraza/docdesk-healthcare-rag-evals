"""T101 (AC-EVL-06): the gate fails when recall@5 or MRR drops past the tolerance."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from ci_gate_compare import GATED, TOLERANCE, check_gate, gate_numbers  # noqa: E402

BASELINE = {"recall@5": 0.9, "mrr": 0.8}


def summary(recall: float, mrr: float) -> dict:
    """A b0_summary shaped dict with only the cells the gate reads."""
    cells = {"recall@5": {"mean": recall}, "mrr": {"mean": mrr}}
    return {"categories": {"all": {"n": 14, **cells}, "single_fact": {"n": 9}}}


def test_ac_evl_06_gate_reads_the_all_row_of_the_summary() -> None:
    assert gate_numbers(summary(0.9, 0.8)) == BASELINE


def test_ac_evl_06_gate_passes_when_numbers_are_unchanged() -> None:
    assert check_gate(BASELINE, BASELINE) == []


def test_ac_evl_06_gate_passes_on_a_drop_inside_the_tolerance() -> None:
    inside = {name: value - TOLERANCE for name, value in BASELINE.items()}
    assert check_gate(inside, BASELINE) == []


def test_ac_evl_06_gate_passes_when_numbers_improve() -> None:
    assert check_gate({"recall@5": 1.0, "mrr": 0.95}, BASELINE) == []


def test_ac_evl_06_gate_fails_on_a_recall_drop_past_the_tolerance() -> None:
    failures = check_gate({"recall@5": 0.9 - TOLERANCE - 0.01, "mrr": 0.8}, BASELINE)
    assert len(failures) == 1
    assert "recall@5" in failures[0]


def test_ac_evl_06_gate_fails_on_an_mrr_drop_past_the_tolerance() -> None:
    failures = check_gate({"recall@5": 0.9, "mrr": 0.8 - TOLERANCE - 0.01}, BASELINE)
    assert len(failures) == 1
    assert "mrr" in failures[0]


def test_ac_evl_06_gate_fails_when_a_gated_metric_is_missing() -> None:
    failures = check_gate({"recall@5": 0.9}, BASELINE)
    assert any("mrr" in failure for failure in failures)


def test_ac_evl_06_gate_fails_when_the_baseline_lacks_a_gated_metric() -> None:
    failures = check_gate(BASELINE, {"recall@5": 0.9})
    assert any("mrr" in failure for failure in failures)


def test_ac_evl_06_gated_metrics_are_recall_at_5_and_mrr() -> None:
    assert GATED == ("recall@5", "mrr")
