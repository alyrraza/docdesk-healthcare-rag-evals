"""The Phase 5 summary table, built by code from the stored technique comparison files."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from docdesk.evals.report_table import table

HEADER = ["technique", "target failure", "n", "change in strict pass (paired interval)",
          "change in recall@5", "tokens billed", "p95 ms (non cached)", "verdict"]

LIMITATIONS = (
    "n is 30 answerable dev items, so every interval is wide and an effect below about 0.15 "
    "cannot be told from noise. Choosing the best of several configs on the same 30 items "
    "overfits, which is why every config tried is listed above.",
    "The judge labels are Claude drafts with Ali review pending, so no human has validated the "
    "judges yet, and kappa rests on 24 independent items.",
    "The policy filter gaps (dose and diagnosis cases) remain open and are not part of these runs.",
    "The injection items (gi-078, gi-079) are not run: they need the fixture loader (T122).",
    "E5 cap 4 was seen before the pre-registration, because its run was made earlier for judge "
    "calibration, so it is not a blind result.",
    "Hybrid retrieval showed no clear difference, and top_k 8 was not completed because the daily "
    "generator token budget was spent.",
    "Chunk size and strategy techniques were not tried: a re-ingest changes chunk ids and "
    "invalidates the stored runs (review finding F8), and a reranker needs a model download "
    "outside the dependency list.",
)


@dataclass(frozen=True)
class Entry:
    """One config tried: its name, the failure it targets, and its stored comparison (or None)."""

    name: str
    target: str
    config: str
    comparison: dict[str, Any] | None


def metric(comparison: dict[str, Any], name: str) -> dict[str, Any]:
    """One overall row of a comparison."""
    return next(r for r in comparison["overall"] if r["metric"] == name)


def strict_cell(comparison: dict[str, Any]) -> tuple[str, str]:
    """Items gained and lost with the paired interval, and the plain verdict phrase."""
    row, s = metric(comparison, "strict_pass"), comparison["strict_pass"]
    change = f"{len(s['gained'])} gained, {len(s['lost'])} lost, rate {row['difference']:+.3f} " \
             f"[{row['low']:+.3f}, {row['high']:+.3f}]"
    if row["low"] > 0 or row["high"] < 0:
        return change, "interval excludes zero"
    return change, "no clear difference"


def number(value: float | int | str | None, spec: str = "{:.0f}") -> str:
    """A number, or the plain words for a value that was never recorded."""
    if isinstance(value, str):
        return value
    return "not recorded" if value is None else spec.format(value)


def entry_row(entry: Entry) -> list[str]:
    """One table row; an unfinished config has no numbers and says so."""
    c = entry.comparison
    if c is None:
        return [entry.name, entry.target, "n/a", "not finished", "n/a", "n/a", "n/a",
                "not completed, the daily generator token budget was spent"]
    change, phrase = strict_cell(c)
    recall = metric(c, "recall")
    verdict = f"kept, {phrase}" if c["rule"]["kept"] else f"not kept, {phrase}"
    return [entry.name, entry.target, str(c["strict_pass"]["answerable"]), change,
            f"{recall['difference']:+.3f}" if recall.get("n") else "n/a",
            number(c["tokens_billed"]["candidate"]), number(c["p95_total_ms"]["candidate"]),
            verdict]


AMENDMENTS = (
    "First amendment (2026-10-15, before any FINAL run): superseded for the final choice by the "
    "second. The one item rule would have turned hybrid noise into a kept technique, so the "
    "candidates became FINAL_SIMPLE (cap 4 alone) and FINAL_FULL (cap 4 plus hybrid, plus top_k 8 "
    "if it passed), with FINAL_FULL frozen only if it beat FINAL_SIMPLE by 2 items.",
    "Second amendment (2026-10-15, before any FINAL_FULL run and any test run): FINAL_FULL and "
    "top_k 8 were not completed because the daily generator token budget was spent (168122 of "
    "170000). FINAL is FINAL_SIMPLE, E5 cap 4 alone, the only technique whose paired interval "
    "excludes zero on dev.",
)


def test_split_lines(split: dict[str, Any] | None) -> list[str]:
    """The held-out result, only when it was run (once, with no tuning afterwards)."""
    if split is None:
        return ["The held-out test split was not run in this report.", ""]
    s = split["strict_pass"]
    rows = [[c["name"], str(r["n"]), f"{r['baseline']:.2f}", f"{r['candidate']:.2f}",
             f"{r['difference']:+.3f} [{r['low']:+.3f}, {r['high']:+.3f}]", r["verdict"]]
            for c in split.get("categories", []) for r in c["rows"]
            if r["metric"] == "strict_pass" and r.get("n")]
    return [
        "## Test split", "",
        f"B0 and FINAL, run once each. Strict pass on {s['answerable']} answerable items: B0 "
        f"{s['baseline']}, FINAL {s['candidate']}. Gained {', '.join(s['gained']) or 'none'}, "
        f"lost {', '.join(s['lost']) or 'none'}. See `test_split_b0_vs_final.md`.", "",
        *table(["category", "n", "B0", "FINAL", "difference (paired interval)", "verdict"], rows),
        "",
    ]


def summary_markdown(entries: list[Entry], test_split: dict[str, Any] | None) -> str:
    """Every config tried, then the limitations, then the test split if it ran."""
    lines = [
        "# Phase 5 lite summary", "",
        "Generated by `scripts/phase5_summary.py` from the stored comparison files. Dev split. "
        "Baseline of record: B0, 15 of 30 strict pass. Strict pass means faithfulness 1.0 and "
        "correctness 1.0 on answerable items. A paired interval that holds zero is written "
        "no clear difference. The verdict follows the pre-registered rule: at least one item "
        "more than B0 and faithfulness not lowered, ties and losses excluded.", "",
        *table(HEADER, [entry_row(e) for e in entries]), "",
        "## Amendments to the FINAL rule", "", *[f"- {text}" for text in AMENDMENTS], "",
        "## Limitations", "", *[f"- {text}" for text in LIMITATIONS], "",
        *test_split_lines(test_split),
    ]
    return "\n".join(lines)
