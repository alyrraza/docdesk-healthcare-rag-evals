"""Decide before calling the model whether the evidence is too weak to answer (AC-GEN-03)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from docdesk.retrieval.types import RetrievalResult


@dataclass(frozen=True)
class AbstainPolicy:
    """Thresholds per retrieval config id, because each config scores on a different scale."""

    thresholds: dict[str, float] = field(default_factory=dict)
    default: float = 0.0

    def threshold_for(self, config_id: str) -> float:
        """The tuned threshold for this config, or the default when none was tuned yet."""
        return self.thresholds.get(config_id, self.default)


def abstain_reason(
    result: RetrievalResult, policy: AbstainPolicy
) -> Literal["no_evidence", "weak_evidence"] | None:
    """Return why to abstain without an LLM call, or None when the evidence is good enough."""
    if not result.chunks:
        return "no_evidence"
    if result.best_score < policy.threshold_for(result.config_id):
        return "weak_evidence"
    return None
