"""T098a (AC-EVL-05): strict pass rate, stage split, label by outcome table, worst five."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import Any

from docdesk.evals.report import report_markdown
from docdesk.evals.report_data import ResultRecord, RunData, build_report
from docdesk.evals.report_sections import (
    label_by_outcome,
    stage_split,
    strict_pass_rate,
    worst_answered,
)
from docdesk.evals.report_usage import ModelUsage


def row(item_id: str, label: str | None = None, trace: dict | None = None,
        **values: Any) -> ResultRecord:
    metrics: dict[str, Any] = {
        "status": "ok", "type": "single_fact", "behavior": "answer", "outcome": "answered",
        "group": f"doc-{item_id}", "recall": 1.0, "hit": 1.0, "mrr": 1.0,
        "context_precision": 0.5, "citation_precision": 1.0, "citation_recall": 1.0,
        "faithfulness": 1.0, "faithfulness_status": "scored", "correctness": 1.0,
        "correctness_status": "scored", "passed": label is None, "tokens_in": 100,
        "tokens_out": 20, "cost_usd": "0.001", "cache_hits": 0, "llm_calls": 3,
    }
    return ResultRecord(item_id, {**metrics, **values}, label, trace or {})


def abstained(item_id: str, label: str | None = None, **values: Any) -> ResultRecord:
    """An answerable item the system declined, so it has no judged scores."""
    return row(item_id, label, outcome="abstained", faithfulness=None, correctness=None,
               passed=False, **values)


def unanswerable(item_id: str) -> ResultRecord:
    return row(item_id, None, type="unanswerable", behavior="abstain", outcome="abstained",
               faithfulness=None, correctness=None, recall=None)


def run(*records: ResultRecord) -> RunData:
    return RunData("run-a", "b0", "dev", "full", list(records))


def test_ac_evl_05_sections_01_strict_pass_needs_both_scores_at_1_on_answerable_items() -> None:
    records = [
        row("gi-001"),                                   # strict pass
        row("gi-002", "incorrect", correctness=0.5),
        row("gi-003", "unfaithful", faithfulness=0.67),
        abstained("gi-004", "retrieval_miss"),           # no scores, so not a strict pass
        unanswerable("gi-005"),                          # not answerable, not counted
    ]
    result = strict_pass_rate(records)
    assert (result.n, result.passed) == (4, 1)
    assert result.cell.interval is not None and result.cell.interval.estimate == 0.25


def test_ac_evl_05_sections_02_stage_split_groups_labels_by_stage() -> None:
    records = [
        row("gi-001"),
        abstained("gi-002", "retrieval_miss"),
        abstained("gi-003", "ranking_miss"),
        abstained("gi-004", "ranking_miss"),
        row("gi-005", "context_overflow", correctness=0.0),
        row("gi-006", "context_distraction", correctness=0.5),
        row("gi-007", "unfaithful", faithfulness=0.5),
        unanswerable("gi-008"),
    ]
    split = stage_split(records)
    assert split.n == 7
    assert split.counts == {"retrieval": 3, "packing": 1, "generation": 2, "pass": 1}
    assert split.labels["retrieval"] == {"ranking_miss": 2, "retrieval_miss": 1}
    assert split.labels["generation"] == {"context_distraction": 1, "unfaithful": 1}


def test_ac_evl_05_sections_03_label_by_outcome_shows_wrong_abstains_under_their_label() -> None:
    records = [
        abstained("gi-001", "retrieval_miss"),
        abstained("gi-002", "retrieval_miss"),
        row("gi-003", "retrieval_miss", correctness=0.0),
        row("gi-004", "missed_refusal", type="adversarial", behavior="refuse"),
        row("gi-005"),
        unanswerable("gi-006"),
    ]
    table = label_by_outcome(records)
    assert table["retrieval_miss"] == {"answered": 1, "abstained": 2}
    assert table["missed_refusal"] == {"answered": 1}
    assert table["no label (passed)"] == {"answered": 1, "abstained": 1}


def trace(claims: list[str], points: list[str]) -> dict[str, Any]:
    return {
        "faithfulness_labels": [{"claim": "c", "label": v} for v in claims],
        "correctness_labels": [{"point": n, "label": v} for n, v in enumerate(points, 1)],
    }


def test_ac_evl_05_sections_04_worst_five_are_ranked_by_lowest_score_then_id() -> None:
    records = [
        row("gi-010", "incorrect", correctness=0.5,
            trace=trace(["supported"], ["covered", "missing"])),
        row("gi-011", "context_overflow", correctness=0.0,
            trace=trace(["supported"], ["missing"])),
        row("gi-012", "unfaithful", faithfulness=0.5,
            trace=trace(["supported", "unsupported"], ["covered"])),
        row("gi-013", "incorrect", correctness=0.0, trace=trace(["supported"], ["missing"])),
        row("gi-014", "incorrect", correctness=0.5,
            trace=trace(["supported"], ["covered", "missing"])),
        row("gi-015"),
        abstained("gi-016", "retrieval_miss"),            # not answered, never listed
    ]
    worst = worst_answered(records)
    assert [w.item_id for w in worst] == ["gi-011", "gi-013", "gi-010", "gi-012", "gi-014"]
    assert worst[0].label == "context_overflow"


def test_ac_evl_05_sections_05_worst_line_states_counts_only() -> None:
    records = [row("gi-020", "incorrect", correctness=0.5,
                   trace={**trace(["supported", "supported", "unsupported"],
                                  ["covered", "missing", "contradicted"]),
                          "used_ids": ["a", "b"], "cited_ids": ["a"]})]
    line = worst_answered(records)[0].line
    assert "correctness 0.50 (1 covered, 1 missing, 1 contradicted)" in line
    assert "faithfulness 1.00 (2 of 3 claims supported)" in line
    assert "recall@k 1.00" in line
    assert "2 chunks in the prompt, 1 cited" in line


def test_ac_evl_05_sections_06_report_headline_is_the_answerable_number_with_a_note() -> None:
    records = [row("gi-001"), row("gi-002", "incorrect", correctness=0.5), unanswerable("gi-003")]
    text = report_markdown(build_report(run(*records)))
    headline = next(line for line in text.splitlines() if line.startswith("Headline"))
    assert "1 of 2 answerable items" in headline and "0.50" in headline
    assert "overall pass rate" in headline and "0.67" in headline
    assert "Unanswerable items pass by abstaining" in text
    for title in ("Where answerable items fail", "Failure label by outcome", "Worst five"):
        assert title in text
    assert "—" not in text and "–" not in text


def test_ac_evl_05_sections_07_tokens_and_cost_per_model_with_a_list_price_note() -> None:
    usage = [ModelUsage("gen-model", 43, 3, 52556, 4000, Decimal("0.0124239"), Decimal("0.0100")),
             ModelUsage("judge-model", 40, 0, 25836, 0, Decimal("0.0295552"), Decimal("0.0295552"))]
    text = report_markdown(replace(build_report(run(row("gi-001"))), model_usage=usage))
    assert "| gen-model | 43 | 3 | 52556 | 4000 | 0.010000 |" in text
    assert "| judge-model | 40 | 0 | 25836 | 0 | 0.029555 |" in text
    assert "list price" in text
