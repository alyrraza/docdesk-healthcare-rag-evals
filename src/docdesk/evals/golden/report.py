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


def absence_report(items: list[ResolvedItem]) -> str:
    """Why: the owner sees what code proved absent, and where, for every unanswerable item."""
    mine = [resolved.item for resolved in items if resolved.item.absent_terms]
    if not mine:
        return "absence check: no unanswerable items"
    lines = [f"absence check: {len(mine)} items"]
    for item in mine:
        count = len(item.absent_terms)
        where = "the whole corpus" if item.absence_scope == "corpus" else item.absence_scope
        noun = "term" if count == 1 else "terms"
        terms = ", ".join(item.absent_terms)
        lines.append(f"{item.id}: {count} {noun} absent from {where} ({terms})")
    return "\n".join(lines)
