"""The one pass rule: every pass count in the harness calls this, so the tables cannot disagree."""

from __future__ import annotations

# An answer passes only when every claim is supported and every key point is covered.
FAITHFUL_AT = 1.0
CORRECT_AT = 1.0


def scores_pass(faithfulness: float | None, correctness: float | None, contradicted: int) -> bool:
    """Why: a judge that failed gives no score, and no score must never read as a pass."""
    if faithfulness is None or correctness is None:
        return False
    return faithfulness >= FAITHFUL_AT and correctness >= CORRECT_AT and contradicted == 0
