"""Counts of verified and draft golden items, so drafts are never mistaken for checked ones."""

from __future__ import annotations

from dataclasses import dataclass

from docdesk.evals.golden.schema import GoldenItem


@dataclass(frozen=True)
class ItemCounts:
    """How many items are hand verified and how many are still drafts, overall and per split."""

    verified: int
    unverified: int
    by_split: dict[str, tuple[int, int]]

    def summary(self) -> str:
        """Verified and unverified counts on separate figures, so drafts are never mistaken."""
        lines = [f"golden items: verified {self.verified}, unverified {self.unverified}"]
        for split, (verified, unverified) in sorted(self.by_split.items()):
            lines.append(f"  {split}: verified {verified}, unverified {unverified}")
        return "\n".join(lines)


def count_found(items: list[GoldenItem]) -> ItemCounts:
    """Count the given items by verification state, overall and per split."""
    by_split: dict[str, tuple[int, int]] = {}
    for item in items:
        verified, unverified = by_split.get(item.split, (0, 0))
        by_split[item.split] = (verified + item.verified, unverified + (not item.verified))
    totals = [sum(pair[index] for pair in by_split.values()) for index in (0, 1)]
    return ItemCounts(totals[0], totals[1], by_split)
