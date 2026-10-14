"""T095 (AC-EVL-05): category tables with intervals, label counts and paired comparison."""

from __future__ import annotations

from typing import Any

from docdesk.evals.report import compare_markdown, report_markdown
from docdesk.evals.report_compare import compare_runs
from docdesk.evals.report_data import (
    RESAMPLES,
    SEED,
    ResultRecord,
    RunData,
    build_report,
)


def ok(item_id: str, item_type: str = "single_fact", **values: Any) -> ResultRecord:
    metrics: dict[str, Any] = {
        "status": "ok", "type": item_type, "behavior": "answer", "outcome": "answered",
        "group": f"doc-{item_id}", "recall": 1.0, "hit": 1.0, "mrr": 1.0,
        "context_precision": 0.5, "citation_precision": 1.0, "citation_recall": 1.0,
        "faithfulness": 1.0, "faithfulness_status": "scored", "correctness": 1.0,
        "correctness_status": "scored", "passed": True, "tokens_in": 100, "tokens_out": 20,
        "judge_tokens": 50, "cost_usd": "0.001", "cache_hits": 1, "llm_calls": 3,
    }
    label = values.pop("label", None)
    return ResultRecord(item_id, {**metrics, **values}, label)


def run(*records: ResultRecord, run_id: str = "run-a") -> RunData:
    return RunData(run_id=run_id, config_id="b0", split="dev", mode="full", records=list(records))


def test_ac_evl_05_report_01_categories_in_order_with_intervals_and_counts() -> None:
    data = run(ok("gi-001", recall=0.0, passed=False, label="retrieval_miss"), ok("gi-002"),
               ok("gi-003", "multi_chunk"), ok("gi-004", "unanswerable", recall=None))
    report = build_report(data)
    assert [c.name for c in report.categories][:3] == ["single_fact", "multi_chunk", "unanswerable"]
    single = report.categories[0]
    assert single.n == 2
    recall = single.metrics["recall"]
    assert recall.n == 2 and recall.interval.estimate == 0.5
    assert recall.interval.low <= 0.5 <= recall.interval.high
    assert report.categories[2].metrics["recall"].n == 0  # None values are not zeros


def test_ac_evl_05_report_02_same_data_gives_the_same_intervals() -> None:
    records = [ok(f"gi-{i:03d}", recall=float(i % 2)) for i in range(1, 11)]
    first = build_report(run(*records)).categories[0].metrics["recall"].interval
    second = build_report(run(*records)).categories[0].metrics["recall"].interval
    assert first == second
    text = report_markdown(build_report(run(*records)))
    assert f"{RESAMPLES} resamples" in text and f"seed {SEED}" in text


def test_ac_evl_05_report_03_failure_labels_and_judge_failures_are_counted() -> None:
    data = run(
        ok("gi-001", passed=False, label="retrieval_miss"),
        ok("gi-002", passed=False, label="retrieval_miss"),
        ok("gi-003", passed=False, label="incorrect"),
        ok("gi-004", faithfulness=None, faithfulness_status="parse_failed"),
        ok("gi-005", correctness=None, correctness_status="RateLimitedError"),
    )
    report = build_report(data)
    assert report.failure_labels == {"retrieval_miss": 2, "incorrect": 1}
    assert report.judge_failures["faithfulness"] == {"parse_failed": 1}
    assert report.judge_failures["correctness"] == {"judge_error": 1}


def test_ac_evl_05_report_04_tokens_cost_and_cache_hits_are_added_up() -> None:
    report = build_report(run(ok("gi-001"), ok("gi-002")))
    assert report.tokens_in == 200 and report.tokens_out == 40
    assert str(report.cost_usd) == "0.002" and report.cache_hits == 2 and report.llm_calls == 6


def test_ac_evl_05_report_05_not_run_items_are_listed_apart_and_not_counted() -> None:
    skipped = ResultRecord("gi-079", {"status": "not_run", "type": "adversarial",
                                      "reason": "not run, needs T122"}, None)
    report = build_report(run(ok("gi-001"), skipped))
    assert report.not_run == [("gi-079", "not run, needs T122")]
    assert report.total_ok == 1 and report.failure_labels == {}
    assert all(c.name != "adversarial" for c in report.categories)
    text = report_markdown(report)
    assert "gi-079" in text and "not run, needs T122" in text


def test_ac_evl_05_report_06_abstain_and_refusal_counts_stay_separate() -> None:
    data = run(
        ok("gi-001", "unanswerable", behavior="abstain", outcome="abstained", recall=None),
        ok("gi-002", "adversarial", behavior="refuse", outcome="refused", recall=None),
        ok("gi-003", "adversarial", behavior="refuse", outcome="answered", recall=None),
    )
    counts = build_report(data).abstention
    assert counts.correct_abstain == 1
    assert counts.correct_refusal == 1 and counts.missed_refusal == 1


def test_ac_evl_05_report_07_markdown_has_no_em_or_en_dash() -> None:
    skipped = ResultRecord("gi-079", {"status": "not_run", "type": "adversarial",
                                      "reason": "not run, needs T122"}, None)
    text = report_markdown(build_report(run(ok("gi-001", recall=None), skipped)))
    assert "—" not in text and "–" not in text


def test_ac_evl_05_compare_01_paired_on_the_items_both_runs_have() -> None:
    base = run(*[ok(f"gi-{i:03d}", correctness=0.5) for i in range(1, 21)], run_id="base")
    better = run(*[ok(f"gi-{i:03d}", correctness=1.0) for i in range(1, 21)], run_id="cand")
    result = compare_runs(base, better)
    row = next(r for r in result.rows if r.metric == "correctness")
    assert row.n_paired == 20 and row.paired.mean_difference == 0.5
    assert row.paired.verdict == "candidate is better"


def test_ac_evl_05_compare_02_items_missing_from_one_run_are_left_out_and_reported() -> None:
    base = run(ok("gi-001"), ok("gi-002"), run_id="base")
    other = run(ok("gi-001"), ok("gi-003"), run_id="cand")
    result = compare_runs(base, other)
    assert result.shared == 1 and result.only_baseline == ["gi-002"]
    assert result.only_candidate == ["gi-003"]


def test_ac_evl_05_compare_03_no_gap_is_reported_as_no_clear_difference() -> None:
    values = [0.0, 1.0] * 5
    base = run(*[ok(f"gi-{i:03d}", faithfulness=v) for i, v in enumerate(values, 1)], run_id="b")
    cand = run(*[ok(f"gi-{i:03d}", faithfulness=v) for i, v in enumerate(values, 1)], run_id="c")
    row = next(r for r in compare_runs(base, cand).rows if r.metric == "faithfulness")
    assert row.paired.verdict == "no clear difference"
    assert "no clear difference" in compare_markdown(compare_runs(base, cand))
