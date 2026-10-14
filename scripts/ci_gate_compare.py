"""The retrieval gate decision (T101, AC-EVL-06): current numbers against the stored ones.

Pure functions, so the rule can be tested without a database or a model. The numbers come from
the summary that scripts/b0_summary.py builds, the same code the B0 report uses.
"""

from __future__ import annotations

from typing import Any

GATED = ("recall@5", "mrr")
# Absolute drop allowed below the stored number. Reasoning is in docs/DECISIONS.md (2026-10-14).
TOLERANCE = 0.04


def gate_numbers(summary: dict[str, Any]) -> dict[str, float]:
    """Why: the gate watches only the all-items mean of each gated metric, nothing else."""
    cells = summary["categories"]["all"]
    return {name: cells[name]["mean"] for name in GATED if name in cells}


def check_gate(
    current: dict[str, float], baseline: dict[str, float], tolerance: float = TOLERANCE
) -> list[str]:
    """Why: CI needs one readable line per failed metric, and an empty list means pass."""
    failures = []
    for name in GATED:
        if name not in baseline:
            failures.append(f"{name}: the stored baseline has no value")
        elif name not in current:
            failures.append(f"{name}: the current run has no value")
        elif current[name] < baseline[name] - tolerance:
            failures.append(
                f"{name}: {current[name]:.4f} is below the stored {baseline[name]:.4f}"
                f" by more than the tolerance {tolerance}"
            )
    return failures
