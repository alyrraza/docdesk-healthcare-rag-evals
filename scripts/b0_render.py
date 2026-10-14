"""Markdown for the T097 summary (see b0_summary.py for the numbers). No dash characters."""

from __future__ import annotations

from typing import Any

from b0_summary import KS, TEXT_LIMIT, Worst


def plain(text: str) -> str:
    """Why: the docs style check bans em and en dashes, and chunk text contains them."""
    return text.replace("—", "-").replace("–", "-")


def fmt(stats: dict[str, Any] | None) -> str:
    """One table cell: mean and interval, or n/a."""
    if stats is None:
        return "n/a"
    return f"{stats['mean']:.2f} [{stats['low']:.2f}, {stats['high']:.2f}]"


def render_markdown(summary: dict[str, Any], worst: list[Worst]) -> str:
    """The summary and the worst items as markdown, without any dash characters."""
    k = summary["top_k"]
    cols = [f"recall@{n}" for n in KS] + [f"hit@{k}", "mrr", f"all_gold@{k}"]
    lines = [
        "# B0 retrieval only, dev split",
        "",
        f"Intervals are 95 percent bootstrap intervals, {summary['resamples']} resamples, "
        f"seed {summary['seed']}. Answerable items only; k is {k}.",
        "",
        "| category | items | " + " | ".join(cols) + " |",
        "|---|---|" + "---|" * len(cols),
    ]
    for name, entry in summary["categories"].items():
        cells = " | ".join(fmt(entry.get(metric)) for metric in cols)
        lines.append(f"| {name} | {entry['n']} | {cells} |")
    lines += ["", "## Retrieval stage failure labels", ""]
    labels = summary["failure_labels"]
    lines += [f"- {name}: {labels.get(name, 0)}" for name in ("retrieval_miss", "ranking_miss")]
    lines += ["", "## Top-1 dense score (no threshold decision here)", "",
              "| category | items | min | median | max |", "|---|---|---|---|---|"]
    for name, s in summary["top1_scores"].items():
        lines.append(f"| {name} | {s['n']} | {s['min']:.3f} | {s['median']:.3f} | {s['max']:.3f} |")
    lines += ["", "## Five worst answerable items", ""]
    for entry in worst:
        row = entry.row
        lines += [f"### {row.id} ({row.type})", "", f"Question: {plain(row.question)}", ""]
        for label in entry.missed:
            rank = entry.found_at[label]
            where = "not among the candidates" if rank is None else f"found at rank {rank}"
            lines.append(f"- missed gold entry: {plain(label)} ({where})")
        lines.append("- top 3 chunks:")
        for n, hit in enumerate(row.ranked[:3], start=1):
            lines.append(f"  {n}. {plain(hit.title)} (score {hit.score:.3f}): "
                         f"{plain(hit.text)[:TEXT_LIMIT]}")
        lines.append("")
    return "\n".join(lines)
