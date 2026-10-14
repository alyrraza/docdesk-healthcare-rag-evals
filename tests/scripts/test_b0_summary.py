"""T097: the retrieval summary of a B0 run is computed from ranked chunks, with no model."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from b0_render import render_markdown  # noqa: E402
from b0_summary import Hit, ItemRow, summarize, worst_items  # noqa: E402


def hits(*ids: str) -> list[Hit]:
    """Ranked hits with falling scores 0.9, 0.8, ..."""
    return [Hit(i, "Doc", round(0.9 - 0.1 * n, 2), f"text {i} \u2014 end")
            for n, i in enumerate(ids)]


def row(item_id: str, kind: str, gold: list[set[str]], ranked: list[str]) -> ItemRow:
    answer = bool(gold)
    return ItemRow(item_id, kind, "answer" if answer else "abstain", f"question {item_id}?",
                   [frozenset(g) for g in gold], [f"entry {n}" for n in range(len(gold))],
                   hits(*ranked), item_id)


ROWS = [
    row("a", "single_fact", [{"g1"}], ["g1", "x", "y", "z", "w"]),
    row("b", "single_fact", [{"g2"}], ["x", "y", "g2", "z", "w"]),
    row("c", "single_fact", [{"g3"}], ["x", "y", "z", "w", "v", "g3"]),
    row("d", "single_fact", [{"g4"}], ["x", "y", "z", "w", "v", "u"]),
    row("e", "multi_chunk", [{"m1"}, {"m2"}], ["m1", "m2", "x", "y", "z"]),
    row("f", "multi_chunk", [{"n1"}, {"n2"}], ["n1", "x", "y", "z", "w"]),
    row("u", "unanswerable", [], ["x", "y"]),
]


def test_ac_evl_02_b0_01_recall_at_1_3_5_hit_and_mrr_per_category() -> None:
    summary = summarize(ROWS, top_k=5)
    single = summary["categories"]["single_fact"]
    assert single["n"] == 4
    assert single["recall@1"]["mean"] == 0.25
    assert single["recall@3"]["mean"] == 0.5
    assert single["recall@5"]["mean"] == 0.5
    assert single["hit@5"]["mean"] == 0.5
    assert single["mrr"]["mean"] == (1 + 1 / 3) / 4
    assert summary["categories"]["all"]["n"] == 6
    assert summary["resamples"] == 2000 and summary["seed"] == 0


def test_ac_evl_02_b0_02_multi_chunk_share_with_all_gold_in_top_5() -> None:
    multi = summarize(ROWS, top_k=5)["categories"]["multi_chunk"]
    assert multi["all_gold@5"]["mean"] == 0.5
    assert "all_gold@5" not in summarize(ROWS, top_k=5)["categories"]["single_fact"]


def test_ac_evl_03_b0_03_labels_split_retrieval_miss_from_ranking_miss() -> None:
    # c: gold is a candidate at rank 6, so ranking_miss. d and f: gold is not a candidate.
    labels = summarize(ROWS, top_k=5)["failure_labels"]
    assert labels == {"retrieval_miss": 2, "ranking_miss": 1}


def test_ac_evl_02_b0_04_top1_score_min_median_max_per_category() -> None:
    scores = summarize(ROWS, top_k=5)["top1_scores"]
    assert scores["unanswerable"] == {"n": 1, "min": 0.9, "median": 0.9, "max": 0.9}
    assert scores["single_fact"]["n"] == 4


def test_ac_evl_02_b0_05_worst_items_are_lowest_recall_first_with_missed_entries() -> None:
    worst = worst_items(ROWS, top_k=5, count=2)
    assert [w.row.id for w in worst] == ["c", "d"]  # both recall 0, so the id breaks the tie
    assert worst[0].missed == ["entry 0"] and worst[0].found_at == {"entry 0": 6}
    assert worst[1].found_at == {"entry 0": None}


def test_ac_evl_06_b0_06_markdown_has_no_dash_characters() -> None:
    text = render_markdown(summarize(ROWS, top_k=5), worst_items(ROWS, top_k=5, count=2))
    assert "—" not in text and "–" not in text
    assert "recall@1" in text and "2000 resamples" in text
