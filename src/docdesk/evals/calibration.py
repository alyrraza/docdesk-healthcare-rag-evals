"""The judge calibration summary: natural and synthetic agreement, never pooled (T100, AC-EVL-07).

Everything the report says comes from this dictionary, and the dictionary comes from the joined
outputs, so no number in the report is typed by hand.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from docdesk.evals.calib_join import JudgedOutput
from docdesk.evals.calib_measures import (
    Measure,
    SetResult,
    disagreements,
    evaluate,
    ref_faithful,
)
from docdesk.evals.stats import DEFAULT_CONFIDENCE

# Output numbers on the blind sheets that were marked for Ali's review (DECISIONS.md, 2026-10-14).
NATURAL_BORDERLINE = frozenset({8, 16, 20, 22, 25, 27})
SYNTHETIC_BORDERLINE = frozenset({7, 8})
UNREVIEWED = ("pending", "unknown")


@dataclass(frozen=True)
class Provenance:
    """Who labeled, when, and whether the owner has reviewed the labels."""

    labeled_by: str
    labeled_on: str
    provenance: str
    reviewed_by: str


def provenance_from(document: Mapping[str, Any]) -> Provenance:
    """Read the header of a labels file; a missing reviewed_by counts as not reviewed."""
    return Provenance(str(document.get("labeled_by", "unknown")),
                      str(document.get("labeled_on", "unknown")),
                      str(document.get("provenance", "")),
                      str(document.get("reviewed_by", "unknown")))


def provenance_sentence(natural: Provenance, synthetic: Provenance) -> str:
    """Why: a reader must learn first what the labels are, before any number."""
    pending = [name for name, p in (("natural", natural), ("synthetic", synthetic))
               if p.reviewed_by in UNREVIEWED]
    if len(pending) == 2:
        return ("These labels were drafted by Claude and have not been reviewed by Ali, so the "
                "agreement numbers below measure the judge against Claude drafted labels, not "
                "against human labels.")
    if pending:
        return (f"The {pending[0]} labels were drafted by Claude and have not been reviewed by "
                f"Ali, so the agreement numbers for that set measure the judge against Claude "
                f"drafted labels. The other set was reviewed by {natural.reviewed_by}.")
    return (f"The labels were drafted by Claude and reviewed by {natural.reviewed_by} "
            f"(natural) and {synthetic.reviewed_by} (synthetic).")


def measure_dict(m: Measure) -> dict[str, Any]:
    """One measure as plain data, with the kappa interval spelled out."""
    return {"name": m.name, "labels": list(m.labels), "n": m.n, "table": m.table,
            "agreement": m.agreement, "kappa": m.kappa, "kappa_text": m.kappa_text,
            "interval": asdict(m.interval) if m.interval else None,
            "majority_share": m.majority, "unstable": m.unstable}


def variant_dict(outputs: Sequence[JudgedOutput], resamples: int, seed: int) -> dict[str, Any]:
    """All measures for one choice of outputs (every output, or without the borderline ones)."""
    result: SetResult = evaluate(outputs, resamples=resamples, seed=seed)
    detection = result.detection
    return {
        "n_outputs": len(outputs),
        "measures": {name: measure_dict(m) for name, m in result.measures.items()},
        "detection": {**asdict(detection), "recall": detection.recall,
                      "precision": detection.precision},
        "excluded_no_faithfulness_score": result.excluded,
    }


def set_dict(outputs: Sequence[JudgedOutput], resamples: int, seed: int) -> dict[str, Any]:
    """One set (natural or synthetic) with its two variants and its disagreement list."""
    kept = [o for o in outputs if not o.borderline]
    return {
        "n_outputs": len(outputs),
        "borderline_numbers": sorted(o.n for o in outputs if o.borderline),
        "reference_faithful": sum(1 for o in outputs if ref_faithful(o)),
        "variants": {"all": variant_dict(outputs, resamples, seed),
                     "without_borderline": variant_dict(kept, resamples, seed)},
        "disagreements": [asdict(d) for d in disagreements(outputs)],
    }


def build_summary(
    natural: Sequence[JudgedOutput], synthetic: Sequence[JudgedOutput],
    natural_labels: Provenance, synthetic_labels: Provenance, judge: Mapping[str, Any],
    *, resamples: int, seed: int,
) -> dict[str, Any]:
    """The whole report as data; the two sets are computed apart and are never combined."""
    return {
        "provenance": provenance_sentence(natural_labels, synthetic_labels),
        "labels": {"natural": asdict(natural_labels), "synthetic": asdict(synthetic_labels)},
        "judge": dict(judge),
        "bootstrap": {"resamples": resamples, "seed": seed, "confidence": DEFAULT_CONFIDENCE},
        "sets": {"natural": set_dict(natural, resamples, seed),
                 "synthetic": set_dict(synthetic, resamples, seed)},
    }
