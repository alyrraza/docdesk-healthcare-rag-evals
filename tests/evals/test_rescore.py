"""F1: rows stored under the old pass rule are re-scored from their stored scores, no model call."""

from __future__ import annotations

from typing import Any

from docdesk.evals.rescore import rescored


def row(**values: Any) -> dict[str, Any]:
    base = {"status": "ok", "behavior": "answer", "outcome": "answered", "passed": True,
            "faithfulness": 1.0, "faithfulness_status": "scored", "correctness": 1.0,
            "correctness_status": "scored", "contradicted": 0}
    return {**base, **values}


def test_ac_evl_08_rescore_01_a_full_pass_does_not_change() -> None:
    assert not rescored(row(), None, {}).changed


def test_ac_evl_08_rescore_02_a_row_with_a_label_keeps_it() -> None:
    result = rescored(row(faithfulness=0.5, passed=False), "unfaithful", {})
    assert not result.changed and result.failure_label == "unfaithful"


def test_ac_evl_08_rescore_03_a_parse_failure_that_passed_becomes_judge_failure() -> None:
    old = row(faithfulness=None, faithfulness_status="parse_failed")
    result = rescored(old, None, {"answer": "x"})
    assert result.changed and result.failure_label == "judge_failure"
    assert result.metrics["passed"] is False
    assert result.trace["rescored"]["old_passed"] is True and result.trace["answer"] == "x"


def test_ac_evl_08_rescore_04_no_claims_without_a_judge_failure_becomes_other() -> None:
    old = row(faithfulness=None, faithfulness_status="no_claims")
    assert rescored(old, None, {}).failure_label == "other"


def test_ac_evl_08_rescore_05_abstains_and_not_run_rows_are_left_alone() -> None:
    abstain = row(behavior="abstain", outcome="abstained", faithfulness=None, correctness=None)
    assert not rescored(abstain, None, {}).changed
    assert not rescored({"status": "not_run"}, None, {}).changed
