"""The markdown text of the abstain threshold trade-off report (T102a)."""

from __future__ import annotations

from typing import Any

HEADER = (
    "| threshold | answerable wrongly abstained | of which B0 had answered | "
    "unanswerable abstained before generation | generator calls saved |"
)


def render_markdown(report: dict[str, Any]) -> str:
    """Why: the decision, the facts behind it and the table live in one reviewed document."""
    facts, rows = report["facts"], report["sweep"]
    done, total = facts["unanswerable_generator_abstained"]
    lines = [
        "# Abstain threshold trade-off, B0 dev split",
        "",
        "Analysis only (T102a). No code path reads a threshold other than 0.0.",
        "",
        "## Decision",
        "",
        "The B0 abstain threshold stays 0.0 (owner decision). It is not tuned into B0. A "
        "threshold becomes a technique of Phase 5, compared with B0 by a paired comparison on "
        "the same items.",
        "",
        "## What the B0 dev rows show",
        "",
        f"- The generator already abstained on {done} of {total} unanswerable dev items. A "
        "threshold would only save those generator calls, not add a correct abstain.",
        f"- Top-1 dense score of the {facts['answerable_items']} answerable items starts at "
        f"{facts['answerable_top1_min']:.3f} (median {facts['answerable_top1_median']:.3f}). "
        f"Unanswerable items go up to {facts['unanswerable_top1_max']:.3f} "
        f"(median {facts['unanswerable_top1_median']:.3f}).",
        f"- The ranges {'overlap' if facts['ranges_overlap'] else 'do not overlap'}: "
        f"{facts['answerable_below_unanswerable_max']} answerable items score at or below the "
        f"highest unanswerable score, and {facts['unanswerable_above_answerable_min']} "
        "unanswerable items score at or above the lowest answerable score.",
        f"- B0 abstained on {facts['answerable_generator_abstained']} of "
        f"{facts['answerable_items']} answerable items already (wrong abstain by the generator).",
        "",
        "## Table",
        "",
        "Rule: abstain before generation when the best score is below the threshold (a score equal "
        "to the threshold is kept). Calls saved counts every dev item below the threshold that "
        "reached the generator in the stored B0 run; items refused by policy are not counted.",
        "",
        HEADER,
        "|---|---|---|---|---|",
    ]
    lines += [
        f"| {r['threshold']:.2f} | {r['answerable_wrongly_abstained']} | "
        f"{r['answerable_lost_answers']} | {r['unanswerable_abstained']} | "
        f"{r['generator_calls_saved']} |"
        for r in rows
    ]
    lines += [
        "",
        "Source: top-1 scores from re-running B0 retrieval on the dev split (dense, no model call) "
        "and outcomes from the stored B0 full dev run. Per item data is in the json file.",
        "",
    ]
    return "\n".join(lines)
