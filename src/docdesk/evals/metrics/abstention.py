"""Abstain and refuse counts (T092): different outcomes, so different counters."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from docdesk.evals.outcome import Behavior, Outcome, outcome_cell


def ratio(part: int, whole: int) -> float | None:
    """A share, or None when there was nothing to measure it on."""
    return part / whole if whole else None


@dataclass(frozen=True)
class AbstentionCounts:
    """How many items fell in each cell; abstain (no evidence) and refusal (policy) stay apart."""

    correct_answer: int = 0
    correct_abstain: int = 0
    wrong_abstain: int = 0
    missed_abstain: int = 0
    correct_refusal: int = 0
    wrong_refusal: int = 0
    missed_refusal: int = 0
    errors: int = 0

    @property
    def abstain_recall(self) -> float | None:
        """Of the items that should abstain, the share that did."""
        return ratio(self.correct_abstain, self.correct_abstain + self.missed_abstain)

    @property
    def abstain_precision(self) -> float | None:
        """Of all abstains outside the refusal items, the share that were right."""
        return ratio(self.correct_abstain, self.correct_abstain + self.wrong_abstain)

    @property
    def refusal_recall(self) -> float | None:
        """Of the items that should be refused, the share that were."""
        return ratio(self.correct_refusal, self.correct_refusal + self.missed_refusal)


def count_cells(pairs: Iterable[tuple[Behavior, Outcome]]) -> AbstentionCounts:
    """Count (expected behavior, actual outcome) pairs into the cells."""
    cells = Counter(outcome_cell(behavior, outcome) for behavior, outcome in pairs)
    names = {**{name: name for name in AbstentionCounts.__dataclass_fields__}, "error": "errors"}
    return AbstentionCounts(**{names[cell]: count for cell, count in cells.items()})
