"""F18: abstention precision and recall carry an interval, and zero width cells say why."""

from __future__ import annotations

from typing import Any

from docdesk.evals.report import format_cell, report_markdown
from docdesk.evals.report_data import MetricCell, ResultRecord, RunData, build_report
from docdesk.evals.stats import Interval


def ok(item_id: str, behavior: str, outcome: str) -> ResultRecord:
    metrics: dict[str, Any] = {
        "status": "ok", "type": "unanswerable" if behavior == "abstain" else "single_fact",
        "behavior": behavior, "outcome": outcome, "group": f"doc-{item_id}", "recall": None,
        "faithfulness": None, "correctness": None, "passed": True,
    }
    return ResultRecord(item_id, metrics, None)


def data() -> RunData:
    records = [
        ok("a", "abstain", "abstained"), ok("b", "abstain", "abstained"),
        ok("c", "abstain", "answered"), ok("d", "answer", "abstained"),
        ok("e", "answer", "answered"),
    ]
    return RunData("r", "c", "dev", "full", records)


def test_ac_evl_05_abstain_01_precision_and_recall_have_intervals() -> None:
    report = build_report(data())
    recall = report.abstain_rates["abstain_recall"]
    precision = report.abstain_rates["abstain_precision"]
    assert recall.n == 3 and abs(recall.interval.estimate - 2 / 3) < 1e-9
    assert precision.n == 3 and abs(precision.interval.estimate - 2 / 3) < 1e-9
    text = report_markdown(report)
    assert "abstention recall" in text and "abstention precision" in text


def test_ac_evl_05_abstain_02_a_zero_width_interval_is_marked_all_values_equal() -> None:
    cell = MetricCell(4, Interval(1.0, 1.0, 1.0))
    assert format_cell(cell, 4) == "1.00 (all values equal)"
    assert format_cell(MetricCell(4, Interval(0.5, 0.75, 1.0)), 4) == "0.75 [0.50, 1.00]"
