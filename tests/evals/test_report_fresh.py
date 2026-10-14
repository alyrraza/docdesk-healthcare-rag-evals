"""F7: a committed report must equal what the code regenerates, and its summary is built by code."""

from __future__ import annotations

import json

from docdesk.evals.cli_tools import stale
from docdesk.evals.report_data import ResultRecord, RunData, build_report
from docdesk.evals.report_summary import summary_json, summary_of


def run() -> RunData:
    metrics = {"status": "ok", "type": "single_fact", "behavior": "answer",
               "outcome": "answered", "group": "g", "passed": True, "faithfulness": 1.0,
               "correctness": 1.0, "recall": 1.0}
    skipped = ResultRecord("gi-079", {"status": "not_run", "type": "adversarial",
                                      "reason": "not run"}, None)
    return RunData("run-1", "b0", "dev", "full", [ResultRecord("gi-001", metrics, None), skipped])


def test_ac_evl_05_fresh_01_equal_text_is_fresh_and_a_changed_number_is_stale() -> None:
    assert not stale("a\nb\n", "a\r\nb\r\n")  # line endings do not matter
    assert stale("pass rate 0.50", "pass rate 0.51")


def test_ac_evl_05_fresh_02_the_summary_comes_from_code_and_is_stable() -> None:
    report = build_report(run())
    summary = summary_of(report)
    assert summary["run_id"] == "run-1" and summary["answerable_pass_strict"] == 1
    assert summary["items_not_run"] == ["gi-079"] and summary["latency_ms"] is None
    assert summary["tokens_by_model"] is None  # no per call usage: never a guess
    assert summary_json(report) == summary_json(build_report(run()))
    assert json.loads(summary_json(report)) == summary


def test_ac_evl_05_fresh_03_answerable_labels_leave_out_the_unanswerable_items() -> None:
    answerable = ResultRecord("gi-001", {"status": "ok", "type": "single_fact",
                                         "behavior": "answer", "outcome": "abstained",
                                         "group": "a", "passed": False}, "wrong_abstain")
    refuse = ResultRecord("gi-002", {"status": "ok", "type": "adversarial", "behavior": "refuse",
                                     "outcome": "answered", "group": "b", "passed": False},
                          "missed_refusal")
    data = RunData("r", "b0", "dev", "full", [answerable, refuse])
    assert summary_of(build_report(data))["answerable_labels"] == {"wrong_abstain": 1}
