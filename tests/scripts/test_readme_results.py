"""AC-DEP-05: the README results block is built from committed result files, never typed by hand."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from readme_results import END, START, render_results, splice  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def comparison(technique: str, split: str, base: int, cand: int, n: int, low: float,
               high: float, verdict: str) -> dict:
    """The few fields of a *_vs_b0.json file the README reads."""
    diff = (cand - base) / n
    return {
        "technique": technique, "split": split, "shared_items": n,
        "strict_pass": {"answerable": n, "baseline": base, "candidate": cand,
                        "gained": ["a"] * max(cand - base, 0), "lost": ["b"] * max(base - cand, 0)},
        "overall": [{"metric": "strict_pass", "n": n, "baseline": base / n,
                     "candidate": cand / n, "difference": diff, "low": low, "high": high,
                     "verdict": verdict}],
    }


def write(folder: Path, name: str, data: dict) -> None:
    """Store one synthetic result file."""
    (folder / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")


def synthetic(folder: Path, with_test: bool) -> None:
    """A dev result for cap 4 and hybrid, and optionally a test split result."""
    write(folder, "e5_cap4_vs_b0",
          comparison("e5_cap4", "dev", 15, 19, 30, 0.033, 0.267, "candidate is better"))
    write(folder, "e3_hybrid_vs_b0",
          comparison("e3_hybrid", "dev", 15, 16, 30, -0.133, 0.2, "no clear difference"))
    if with_test:
        write(folder, "test_split_b0_vs_final",
              comparison("test_split_b0_vs_final", "test", 13, 15, 20, -0.1, 0.3,
                         "no clear difference"))


def test_ac_dep_05_dev_block_shows_counts_interval_and_the_no_clear_difference_rows(
    tmp_path: Path,
) -> None:
    synthetic(tmp_path, with_test=False)
    text = render_results(tmp_path)
    assert "15 of 30" in text and "19 of 30" in text and "16 of 30" in text
    assert "+0.033, +0.267" in text
    assert text.count("no clear difference") >= 1


def test_ac_dep_05_without_a_test_file_the_test_split_is_called_pending(tmp_path: Path) -> None:
    synthetic(tmp_path, with_test=False)
    assert "test split result is pending" in render_results(tmp_path)


def test_ac_dep_05_with_a_test_file_the_test_numbers_appear_and_pending_goes_away(
    tmp_path: Path,
) -> None:
    synthetic(tmp_path, with_test=True)
    text = render_results(tmp_path)
    assert "13 of 20" in text and "15 of 20" in text
    assert "result is pending" not in text


def test_ac_dep_05_block_never_claims_human_validation_or_final_dev_numbers(
    tmp_path: Path,
) -> None:
    synthetic(tmp_path, with_test=False)
    text = render_results(tmp_path).lower()
    assert "claude drafts" in text and "review pending" in text
    assert "human validated" not in text and "human-validated" not in text


def test_ac_dep_05_block_has_no_em_or_en_dash(tmp_path: Path) -> None:
    synthetic(tmp_path, with_test=True)
    text = render_results(tmp_path)
    assert "\u2014" not in text and "\u2013" not in text


def test_ac_dep_05_splice_replaces_only_the_marked_block() -> None:
    readme = f"top\n{START}\nold\n{END}\nbottom\n"
    assert splice(readme, "new") == f"top\n{START}\nnew\n{END}\nbottom\n"


def test_ac_dep_05_committed_readme_matches_the_committed_results() -> None:
    """Fails when a result file changed and nobody ran python scripts/readme_results.py."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert splice(readme, render_results(ROOT / "evals" / "results")) == readme


def test_ac_dep_05_techniques_that_did_not_finish_are_listed(tmp_path: Path) -> None:
    synthetic(tmp_path, with_test=False)
    final = comparison("final", "dev", 15, 19, 30, 0.033, 0.267, "candidate is better")
    final["not_completed"] = ["top_k 8: not completed, stopped by the daily token budget."]
    write(tmp_path, "final_vs_b0", final)
    assert "top_k 8: not completed" in render_results(tmp_path)


def test_ac_dep_05_test_paragraph_says_the_dev_gain_was_not_confirmed(tmp_path: Path) -> None:
    synthetic(tmp_path, with_test=True)
    text = render_results(tmp_path)
    assert "does not confirm the dev gain" in text
    assert "consistent with the dev result" not in text
