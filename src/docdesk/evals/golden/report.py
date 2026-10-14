"""Plain text reports about resolved golden items, printed by the batch check script."""

from __future__ import annotations

from docdesk.evals.golden.loader import ResolvedItem


def duplicate_report(items: list[ResolvedItem]) -> str:
    """Why: the owner sees every quote that more than one document holds and how it is covered."""
    if not items:
        return "duplicate evidence check: no items"
    lines = [f"duplicate evidence check: {len(items)} items"]
    clean = 0
    for resolved in items:
        for number, entry in enumerate(resolved.evidence, start=1):
            if not entry.also_in:
                clean += 1
                continue
            alt = set(resolved.item.gold_evidence[number - 1].alt_sources)
            cover = (
                "listed as alt_sources" if set(entry.also_in) <= alt else "named in the question"
            )
            lines.append(
                f"{resolved.item.id} quote {number}: also in {', '.join(entry.also_in)} ({cover})"
            )
    lines.append(f"{clean} quotes occur in one document only")
    return "\n".join(lines)
