"""AC-DEP-02: the demo retrieval command reports hits and fails when the expected one is missing."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from demo_retrieve import Hit, expected_rank, format_hits  # noqa: E402

HITS = [
    Hit("seed:medlineplus:medlineplus-1", "Asthma", 0.71, "Asthma makes it hard to breathe."),
    Hit("seed:medlineplus:medlineplus-387", "Rubella", 0.66, "A rash that starts on the face"),
]


def test_ac_dep_02_expected_rank_is_one_based() -> None:
    assert expected_rank(HITS, "seed:medlineplus:medlineplus-387") == 2


def test_ac_dep_02_expected_rank_is_none_when_the_source_is_missing() -> None:
    assert expected_rank(HITS, "seed:medlineplus:medlineplus-9999") is None


def test_ac_dep_02_format_hits_shows_rank_score_source_and_a_short_snippet() -> None:
    long_hit = [Hit("src", "T", 0.5, "word " * 100)]
    line = format_hits(long_hit, snippet_chars=40)[0]
    assert line.startswith("1  0.500  src  T  ") and len(line) < 100
