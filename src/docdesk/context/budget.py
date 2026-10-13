"""Token budget per prompt slot; starting values from CONTEXT.md, tuned later in experiment E5."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContextBudget:
    """How many input tokens each part of the prompt may use; the slots must add up to the total."""

    total: int = 6000
    system: int = 500
    schema: int = 300
    evidence: int = 4200
    # Single turn on purpose, so history gets nothing (see CONTEXT.md).
    history: int = 0
    question: int = 300
    # Headroom so a long question or a counting error never causes truncation.
    reserve: int = 700

    def __post_init__(self) -> None:
        """Refuse a budget whose slots do not add up, because that hides an over-allocation."""
        slots = self.system + self.schema + self.evidence + self.history
        slots += self.question + self.reserve
        if slots != self.total:
            raise ValueError(f"budget slots add up to {slots}, but the total is {self.total}")
