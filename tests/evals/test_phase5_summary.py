"""Phase 5: the summary table is built by code from the stored comparison files."""

from __future__ import annotations

from typing import Any

from docdesk.evals.phase5_summary import Entry, summary_markdown


def comparison(
    strict_diff: float, low: float, high: float, gained: int, lost: int
) -> dict[str, Any]:
    return {
        "shared_items": 44, "warnings": [],
        "overall": [
            {"metric": "strict_pass", "n": 30, "baseline": 0.5, "candidate": 0.5 + strict_diff,
             "difference": strict_diff, "low": low, "high": high,
             "verdict": "no clear difference" if low <= 0 <= high else "candidate is better"},
            {"metric": "recall", "n": 30, "baseline": 0.84, "candidate": 0.9,
             "difference": 0.06, "low": 0.0, "high": 0.1, "verdict": "no clear difference"},
        ],
        "strict_pass": {"answerable": 30, "baseline": 15, "candidate": 15 + gained - lost,
                        "gained": ["a"] * gained, "lost": ["b"] * lost},
        "tokens_billed": {"baseline": None, "candidate": 1234},
        "p95_total_ms": {"baseline": None, "candidate": 5000.0},
        "rule": {"improves_by_one_item": gained - lost >= 1, "faithfulness_lowered": False,
                 "kept": gained - lost >= 1},
    }


def entries() -> list[Entry]:
    return [
        Entry("E5 cap 4", "context_overflow", "e5_cap4", comparison(0.133, 0.033, 0.267, 4, 0)),
        Entry("E3 hybrid", "ranking_miss", "e3_hybrid", comparison(0.033, -0.133, 0.2, 4, 3)),
        Entry("E5 top_k 8", "ranking_miss", "e5_topk8", None),
    ]


def test_ac_evl_05_p5sum_01_every_config_is_listed_winners_and_losers_and_unfinished() -> None:
    text = summary_markdown(entries(), test_split=None)
    for name in ("E5 cap 4", "E3 hybrid", "E5 top_k 8"):
        assert name in text
    assert "not finished" in text


def test_ac_evl_05_p5sum_02_an_interval_with_zero_says_no_clear_difference_not_improved() -> None:
    text = summary_markdown(entries(), test_split=None)
    hybrid = next(line for line in text.splitlines() if line.startswith("| E3 hybrid"))
    assert "no clear difference" in hybrid and "improved" not in hybrid
    cap = next(line for line in text.splitlines() if line.startswith("| E5 cap 4"))
    assert "kept" in cap and "interval excludes zero" in cap


def test_ac_evl_05_p5sum_03_the_limitations_are_stated_plainly() -> None:
    text = summary_markdown(entries(), test_split=None)
    for phrase in ("30 answerable dev items", "Claude drafts", "review pending",
                   "dose and diagnosis", "injection items", "re-ingest"):
        assert phrase in text
    assert "human validated" not in text and "hand labeled" not in text
    assert "—" not in text and "–" not in text


def test_ac_evl_05_p5sum_04_the_test_split_section_appears_only_when_it_was_run() -> None:
    assert "Test split" not in summary_markdown(entries(), test_split=None)
    assert "not run" in summary_markdown(entries(), test_split=None).lower()
    split = {"strict_pass": {"answerable": 14, "baseline": 7, "candidate": 9, "gained": ["x", "y"],
                             "lost": []}, "shared_items": 30}
    assert "Test split" in summary_markdown(entries(), test_split=split)


def test_ac_evl_05_p5sum_04_not_completed_configs_say_why_and_amendments_are_listed() -> None:
    text = summary_markdown(entries(), test_split=None)
    topk = next(line for line in text.splitlines() if line.startswith("| E5 top_k 8"))
    assert "not completed" in topk and "token budget" in topk
    assert "## Amendments to the FINAL rule" in text
    assert "superseded" in text and "FINAL_SIMPLE" in text


def test_ac_evl_05_p5sum_05_the_new_limitations_are_stated() -> None:
    text = summary_markdown(entries(), test_split=None)
    for phrase in ("cap 4 was seen before", "no clear difference", "top_k 8 was not completed"):
        assert phrase in text


def test_ac_evl_05_p5sum_06_the_test_split_shows_each_category_with_its_n() -> None:
    split = comparison(0.1, -0.1, 0.3, 3, 1)
    split["split"] = "test"
    split["categories"] = [{"name": "single_fact", "rows": [
        {"metric": "strict_pass", "n": 7, "baseline": 0.5, "candidate": 0.6, "difference": 0.1,
         "low": -0.1, "high": 0.3, "verdict": "no clear difference"}]}]
    text = summary_markdown(entries(), test_split=split)
    assert "## Test split" in text and "single_fact" in text and "| 7 |" in text
