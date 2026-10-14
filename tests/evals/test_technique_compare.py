"""Phase 5: the paired comparison of a technique run against B0, per category and overall."""

from __future__ import annotations

from typing import Any

from docdesk.evals.report_data import ResultRecord, RunData
from docdesk.evals.technique_compare import compare_technique, technique_json, technique_markdown


def item(item_id: str, kind: str = "single_fact", strict: bool = True, **values: Any):
    metrics: dict[str, Any] = {
        "status": "ok", "type": kind, "behavior": "answer", "outcome": "answered",
        "group": f"doc-{item_id}", "recall": 1.0, "mrr": 1.0, "faithfulness": 1.0,
        "correctness": 1.0 if strict else 0.5, "passed": strict,
    }
    metrics.update(values)
    return ResultRecord(item_id, metrics, None if strict else "incorrect")


def run(run_id: str, records: list[ResultRecord]) -> RunData:
    return RunData(run_id, "b0", "dev", "full", records, identity={"judge_model": "j"})


def base() -> RunData:
    return run("base", [item(f"gi-{n:03d}", strict=n > 5) for n in range(1, 21)])


def test_ac_evl_05_tech_01_counts_items_gained_and_lost_on_the_strict_rate() -> None:
    better = run("cand", [item(f"gi-{n:03d}", strict=n > 2) for n in range(1, 21)])
    result = compare_technique("t", base(), better)
    assert result["strict_pass"]["baseline"] == 15 and result["strict_pass"]["candidate"] == 18
    assert result["strict_pass"]["gained"] == ["gi-003", "gi-004", "gi-005"]
    assert result["strict_pass"]["lost"] == []
    assert result["rule"]["improves_by_one_item"] is True


def test_ac_evl_05_tech_02_a_tie_or_a_faithfulness_drop_is_not_kept() -> None:
    tie = compare_technique("t", base(), base())
    assert tie["rule"]["kept"] is False
    worse = run("cand", [item(f"gi-{n:03d}", strict=True, faithfulness=0.5 if n == 1 else 1.0)
                         for n in range(1, 21)])
    result = compare_technique("t", base(), worse)
    assert result["rule"]["improves_by_one_item"] and result["rule"]["faithfulness_lowered"]
    assert result["rule"]["kept"] is False


def test_ac_evl_05_tech_03_an_interval_with_zero_never_reads_as_an_improvement() -> None:
    better = run("cand", [item(f"gi-{n:03d}", strict=n > 4) for n in range(1, 21)])
    text = technique_markdown(compare_technique("t", base(), better))
    assert "no clear difference" in text
    assert "candidate is better" not in text


def test_ac_evl_05_tech_04_there_is_a_row_per_category_and_markdown_has_no_dashes() -> None:
    records = [item("gi-001", "single_fact"), item("gi-002", "multi_chunk", strict=False)]
    result = compare_technique("t", run("b", records), run("c", records))
    assert [c["name"] for c in result["categories"]] == ["single_fact", "multi_chunk"]
    text = technique_markdown(result)
    assert "—" not in text and "–" not in text
    assert technique_json(result).endswith("\n")


def test_ac_evl_05_tech_05_legacy_tokens_and_latency_say_not_recorded() -> None:
    result = compare_technique("t", base(), base())
    assert result["tokens_billed"] == {"baseline": None, "candidate": None}
    assert result["p95_total_ms"] == {"baseline": None, "candidate": None}


def test_ac_obs_03_tech_06_a_percentile_over_fewer_than_five_items_is_not_shown() -> None:
    def timed(record: ResultRecord) -> ResultRecord:
        latency = {"retrieval_ms": 500.0, "total_ms": 900.0, "cache_hit": False}
        return ResultRecord(record.item_id, record.metrics, record.failure_label, latency=latency)

    few = run("cand", [timed(item(f"gi-{n:03d}")) for n in range(1, 4)])
    assert compare_technique("t", base(), few)["p95_total_ms"]["candidate"] == (
        "too few non cached items")


def test_ac_evl_05_tech_09_not_completed_configs_are_listed() -> None:
    result = compare_technique("t", base(), base())
    result["not_completed"] = ["final_full: budget spent"]
    text = technique_markdown(result)
    assert "## Not completed" in text and "final_full: budget spent" in text
    assert "Not completed" not in technique_markdown(compare_technique("t", base(), base()))


def test_ac_evl_05_tech_09_dev_report_labels_the_rule_line_as_a_dev_rule_verdict() -> None:
    better = run("cand", [item(f"gi-{n:03d}", strict=n > 2) for n in range(1, 21)])
    text = technique_markdown(compare_technique("t", base(), better))
    assert "Dev rule verdict: kept." in text
    assert "Result:" not in text


def test_ac_evl_05_tech_10_test_split_report_prints_no_dev_rule_verdict() -> None:
    better = run("cand", [item(f"gi-{n:03d}", strict=n > 2) for n in range(1, 21)])
    on_test = RunData("cand", "final", "test", "full", better.records,
                      identity={"judge_model": "j"})
    text = technique_markdown(compare_technique("t", base(), on_test))
    assert "verdict: kept" not in text and "not kept" not in text and "Result:" not in text
    assert "Strict pass on answerable items" in text
