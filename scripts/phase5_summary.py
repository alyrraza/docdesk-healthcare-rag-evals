"""Write evals/results/phase5_summary.md from the stored <technique>_vs_b0.json files.

Usage: python scripts/phase5_summary.py
Makes no database or model call. A config with no comparison file is listed as not finished.
"""

from __future__ import annotations

import json

from docdesk.evals.paths import PROJECT_ROOT
from docdesk.evals.phase5_summary import Entry, summary_markdown

RESULTS = PROJECT_ROOT / "evals" / "results"
# Pre-registered order and targets (docs/PHASE5_PROGRESS.md). The second field is the failure label.
CONFIGS = (
    ("E5 per document cap 4", "context_overflow", "e5_cap4"),
    ("E3 hybrid retrieval", "ranking_miss", "e3_hybrid"),
    ("E5 top_n 50", "retrieval_miss", "e5_topn50"),
    ("E5 top_k 8", "ranking_miss, context_overflow", "e5_topk8"),
    ("E4 drop title only chunks", "ranking_miss (gi-014, gi-024)", "e4_title_drop"),
    ("E7 rule based decomposition", "multi entity (gi-047)", "e7_decompose"),
    ("T111a abstain gate 0.55", "unanswerable answered", "t111a_abstain055"),
    ("T111a abstain gate 0.60 (risky)", "unanswerable answered", "t111a_abstain060"),
    ("FINAL = FINAL_SIMPLE (cap 4 alone), frozen", "context_overflow", "final"),
    ("FINAL_FULL (cap 4 plus hybrid)", "all", "final_full"),
)


def load(name: str) -> dict | None:
    """The stored comparison of one config, or None when it has not finished."""
    path = RESULTS / f"{name}_vs_b0.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def main() -> None:
    """Build the entries, add the test split result if its file exists, write the markdown."""
    entries = [Entry(title, target, name, load(name)) for title, target, name in CONFIGS]
    split_path = RESULTS / "test_split_b0_vs_final.json"
    split = json.loads(split_path.read_text(encoding="utf-8")) if split_path.exists() else None
    out = RESULTS / "phase5_summary.md"
    out.write_text(summary_markdown(entries, split), encoding="utf-8", newline="\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
