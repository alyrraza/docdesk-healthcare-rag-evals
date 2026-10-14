"""Abstain threshold trade-off on the B0 dev rows (T102a, AC-GEN-03). Analysis only.

Pure functions over one probe per dev item: its top-1 dense score and what B0 did with it. The
rule is the one in generation/abstain.py: abstain before generation when the best score is
below the threshold. Nothing here changes the threshold that B0 or the live route uses.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import median
from typing import Any

Kind = str  # "answerable", "unanswerable" or "adversarial"


@dataclass(frozen=True)
class Probe:
    """One dev item: its top-1 score and the outcome the stored B0 full run gave it."""

    id: str
    kind: Kind
    top1: float
    outcome: str  # answered, abstained or refused


def thresholds() -> list[float]:
    """Why: the grid is fixed (0.40 to 0.70, step 0.01) and built from integers to avoid drift."""
    return [round(step / 100, 2) for step in range(40, 71)]


def sweep_row(probes: list[Probe], threshold: float) -> dict[str, Any]:
    """What abstaining below this threshold would have done to the B0 dev items."""
    below = [p for p in probes if p.top1 < threshold]
    wrong = [p for p in below if p.kind == "answerable"]
    return {
        "threshold": threshold,
        "answerable_wrongly_abstained": len(wrong),
        "answerable_lost_answers": sum(p.outcome == "answered" for p in wrong),
        "unanswerable_abstained": sum(p.kind == "unanswerable" for p in below),
        # An item refused by policy never reached the generator, so it saves no call.
        "generator_calls_saved": sum(p.outcome != "refused" for p in below),
    }


def facts_of(probes: list[Probe]) -> dict[str, Any]:
    """The numbers the report states in words, taken from the rows and never typed in."""
    answerable = [p for p in probes if p.kind == "answerable"]
    unanswerable = [p for p in probes if p.kind == "unanswerable"]
    lowest, highest = min(p.top1 for p in answerable), max(p.top1 for p in unanswerable)
    return {
        "answerable_items": len(answerable),
        "unanswerable_items": len(unanswerable),
        "unanswerable_generator_abstained": [
            sum(p.outcome == "abstained" for p in unanswerable), len(unanswerable)],
        "answerable_generator_abstained": sum(p.outcome == "abstained" for p in answerable),
        "answerable_top1_min": lowest,
        "answerable_top1_median": median(p.top1 for p in answerable),
        "unanswerable_top1_max": highest,
        "unanswerable_top1_median": median(p.top1 for p in unanswerable),
        "ranges_overlap": lowest <= highest,
        "answerable_below_unanswerable_max": sum(p.top1 <= highest for p in answerable),
        "unanswerable_above_answerable_min": sum(p.top1 >= lowest for p in unanswerable),
    }


def build_report(probes: list[Probe]) -> dict[str, Any]:
    """Why: one plain dict feeds both the json file and the markdown writer."""
    return {
        "config": "b0",
        "split": "dev",
        "rule": "abstain before generation when the best score is below the threshold",
        "b0_threshold": 0.0,
        "facts": facts_of(probes),
        "sweep": [sweep_row(probes, t) for t in thresholds()],
        "items": [asdict(p) for p in sorted(probes, key=lambda p: p.id)],
    }
