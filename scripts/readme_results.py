"""Rebuild the results block of README.md from the committed files in evals/results.

Usage (project root):
    python scripts/readme_results.py            rewrite the block between the markers
    python scripts/readme_results.py --check    exit 1 if the README block is out of date
Only numbers read from the *_vs_b0.json files are printed, so the README cannot drift from them.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
START = "<!-- results:start (written by scripts/readme_results.py, do not edit by hand) -->"
END = "<!-- results:end -->"
CAP4 = "e5_cap4_vs_b0"
TEST_FILE = "test_split_b0_vs_final"
# File stem, then the name the README uses for that setup.
TECHNIQUES = [
    (CAP4, "Cap 4 chunks per document"),
    ("e3_hybrid_vs_b0", "Hybrid dense plus keyword search"),
    ("e5_topn50_vs_b0", "Candidate list of 50 instead of 20"),
    ("e4_title_drop_vs_b0", "Drop chunks that only repeat the title"),
    ("e7_decompose_vs_b0", "Split multi drug questions into sub queries"),
    ("t111a_abstain055_vs_b0", "Abstain when the top score is under 0.55"),
    ("t111a_abstain060_vs_b0", "Abstain when the top score is under 0.60"),
]


def load(folder: Path, stem: str) -> dict[str, Any] | None:
    """Why: a missing result file is a normal state (the test split may not exist yet)."""
    path = folder / f"{stem}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def strict_row(data: dict[str, Any]) -> dict[str, Any]:
    """Why: the strict pass row holds the paired interval, the counts live next to it."""
    return next(r for r in data["overall"] if r["metric"] == "strict_pass")


def interval(data: dict[str, Any]) -> str:
    """Format the paired difference on the pass rate with its 95 percent bootstrap interval."""
    row = strict_row(data)
    return f"{row['difference']:+.3f} [{row['low']:+.3f}, {row['high']:+.3f}]"


def reading(data: dict[str, Any]) -> str:
    """Why: a gap whose interval holds zero must never be worded as an improvement."""
    if strict_row(data)["verdict"] == "candidate is better":
        return "better on dev, interval excludes zero"
    return "no clear difference"


def of(count: int, total: int) -> str:
    """Write a pass count the way the README always does."""
    return f"{count} of {total}"


def dev_table(folder: Path) -> list[str]:
    """One row per technique that has a stored dev comparison against B0."""
    rows = []
    for stem, label in TECHNIQUES:
        data = load(folder, stem)
        if data is None:
            continue
        sp = data["strict_pass"]
        change = f"{len(sp['gained'])} gained, {len(sp['lost'])} lost"
        rows.append(
            f"| {label} | {of(sp['candidate'], sp['answerable'])} | {change} | "
            f"{interval(data)} | {reading(data)} |"
        )
    baseline = load(folder, CAP4)
    first = of(baseline["strict_pass"]["baseline"], baseline["strict_pass"]["answerable"])
    head = ["| setup | strict pass | against B0 | paired change in rate [95% interval] | reading |",
            "|---|---|---|---|---|", f"| B0 baseline | {first} | | | |"]
    return head + rows


def not_completed(folder: Path) -> list[str]:
    """Why: a technique that never finished must be listed, or the table looks complete."""
    data = load(folder, "final_vs_b0")
    return [f"- {note}" for note in (data or {}).get("not_completed", [])]


def test_section(folder: Path) -> list[str]:
    """The test split paragraph, or one line saying it is pending when the file is missing."""
    data = load(folder, TEST_FILE)
    if data is None:
        return ["The test split result is pending. It is run once, after the setup is frozen."]
    sp = data["strict_pass"]
    return [
        "The test split was run once for each setup, with no tuning afterwards. FINAL is the cap 4 "
        f"setup. Strict pass on {sp['answerable']} answerable test questions: B0 "
        f"{of(sp['baseline'], sp['answerable'])}, FINAL {of(sp['candidate'], sp['answerable'])}. "
        f"Paired change in rate {interval(data)}: {reading(data)}. With 20 questions this is weak "
        "evidence, and I read it as consistent with the dev result, not as a confirmed gain.",
    ]


def render_results(folder: Path) -> str:
    """Build the whole README results block from the result files in one folder."""
    cap4 = load(folder, CAP4)
    lines = [
        "### Dev split (30 answerable questions)", "",
        "Strict pass means faithfulness 1.0 and correctness 1.0 on an answerable question. "
        "These are dev numbers. I used them to choose the setup, so they are not final results.",
        "",
        *dev_table(folder), "",
        "Only the cap 4 row has an interval that excludes zero. The cap 4 run was made earlier "
        "for judge calibration, before I wrote down the plan, so it was not a blind test.",
        "",
        *(["Not completed:", "", *not_completed(folder), ""] if not_completed(folder) else []),
        "### Test split", "", *test_section(folder), "",
        "Judge labels are Claude drafts with the author's review pending. Faithfulness and "
        "correctness are scored by a language model judge that I have not yet checked by hand.",
    ]
    if cap4 is None:
        lines = ["No stored dev comparison found in evals/results."]
    return "\n".join(lines)


def splice(readme: str, block: str) -> str:
    """Why: only the marked block is generated, the rest of the README is written by hand."""
    head, _, rest = readme.partition(START)
    _, _, tail = rest.partition(END)
    return f"{head}{START}\n{block}\n{END}{tail}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    path = ROOT / "README.md"
    text = path.read_text(encoding="utf-8")
    updated = splice(text, render_results(ROOT / "evals" / "results"))
    if parser.parse_args().check:
        sys.exit(0 if updated == text else 1)
    path.write_text(updated, encoding="utf-8", newline="\n")
    print("README results block rebuilt")
