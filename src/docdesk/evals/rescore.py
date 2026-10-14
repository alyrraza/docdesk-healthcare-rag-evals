"""Re-apply the one pass rule (F1) to rows stored under the old rule, with no model call."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from docdesk.evals.passing import scores_pass

RULE = "F1 one pass rule"
JUDGE_FAILED = ("parse_failed",)


@dataclass(frozen=True)
class Rescored:
    """The new values of one row, and whether anything changed."""

    metrics: dict[str, Any]
    failure_label: str | None
    trace: dict[str, Any]
    changed: bool


def judge_failed(metrics: dict[str, Any]) -> bool:
    """True when a stored judge status is a parse failure or an error name (not a clean status)."""
    clean = (None, "scored", "no_claims", "skipped", "decided_by_code")
    return any(metrics.get(f"{j}_status") not in clean for j in ("faithfulness", "correctness"))


def no_citation_scores(
    metrics: dict[str, Any], label: str | None, trace: dict[str, Any]
) -> Rescored:
    """F9: a retrieval only row has no answer, so its citation scores are None, not 0.0."""
    keys = ("citation_precision", "citation_recall")
    if all(metrics.get(k) is None for k in keys):
        return Rescored(metrics, label, trace, False)
    note = {"rule": "F9 citation scores are None without an answer",
            "old": {k: metrics.get(k) for k in keys}}
    return Rescored({**metrics, **dict.fromkeys(keys)}, label, {**trace, "rescored": note}, True)


def rescored(metrics: dict[str, Any], label: str | None, trace: dict[str, Any]) -> Rescored:
    """Only an answered answerable item that passed under the old rule can change.

    A row that already has a label stays failed under the new rule with the same label, because
    the new rule fails every item the old rule failed. A row that passed but lacks a judge score
    now fails: judge_failure when a judge failed, otherwise other (for example no claims).
    """
    unchanged = Rescored(metrics, label, trace, False)
    if metrics.get("status") != "ok":
        return unchanged
    if metrics.get("mode") == "retrieval_only":
        return no_citation_scores(metrics, label, trace)
    if label is not None:
        return unchanged
    if metrics.get("behavior") != "answer" or metrics.get("outcome") != "answered":
        return unchanged
    if scores_pass(metrics.get("faithfulness"), metrics.get("correctness"),
                   metrics.get("contradicted", 0)):
        return unchanged
    new_label = "judge_failure" if judge_failed(metrics) else "other"
    note = {"rule": RULE, "old_label": label, "old_passed": metrics.get("passed")}
    return Rescored({**metrics, "passed": False}, new_label, {**trace, "rescored": note}, True)
