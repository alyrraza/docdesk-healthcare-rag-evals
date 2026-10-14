"""The retrieval gate decision (T101, AC-EVL-06): current numbers against the stored ones.

Pure functions, so the rule can be tested without a database or a model. The numbers come from
the summary that scripts/b0_summary.py builds, the same code the B0 report uses.
"""

from __future__ import annotations

import copy
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


def baseline_record(summary: dict[str, Any], config_id: str, config_hash: str) -> dict[str, Any]:
    """Why: the stored file must say which config and how many items its numbers belong to."""
    return {
        "config_id": config_id,
        "config_hash": config_hash,
        "items": summary["categories"]["all"]["n"],
        "tolerance": TOLERANCE,
        "numbers": gate_numbers(summary),
    }


def config_mismatch(record: dict[str, Any], config_id: str, config_hash: str) -> str | None:
    """Why: numbers from another config are not a baseline, so the gate refuses to compare."""
    if record["config_id"] != config_id:
        return f"stored baseline is for config {record['config_id']}, this run is {config_id}"
    if record["config_hash"] != config_hash:
        return "stored baseline config hash differs from this run, write a new baseline"
    return None


def gate_problems(
    record: dict[str, Any], stored: dict[str, Any], config_id: str, config_hash: str
) -> list[str]:
    """Why: one function decides pass or fail, so the real run and the F12 proof share the rule."""
    problems = [m] if (m := config_mismatch(stored, config_id, config_hash)) else []
    return problems + check_gate(record["numbers"], stored["numbers"])


def corrupt_baseline(stored: dict[str, Any], amount: float = 0.1) -> dict[str, Any]:
    """Why: F12 needs proof the gate fails, so this copy claims numbers better than any real run."""
    corrupted = copy.deepcopy(stored)
    corrupted["numbers"] = {name: value + amount for name, value in stored["numbers"].items()}
    return corrupted
