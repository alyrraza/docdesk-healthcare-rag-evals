"""Bootstrap intervals and paired comparison (AC-EVL-05), with a fixed seed for repeatability."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

DEFAULT_RESAMPLES = 2000
DEFAULT_CONFIDENCE = 0.95
DEFAULT_SEED = 0


@dataclass(frozen=True)
class Interval:
    """A mean and the range a repeat of the evaluation would plausibly land in."""

    low: float
    estimate: float
    high: float


@dataclass(frozen=True)
class PairedResult:
    """Candidate minus baseline on the same items, and whether the gap beats the noise."""

    mean_difference: float
    low: float
    high: float
    clear: bool
    verdict: str


def group_totals(values: np.ndarray, groups: Sequence[str] | None) -> tuple[np.ndarray, np.ndarray]:
    """Sum and count per resampling unit: a document if groups are given, else each item."""
    if groups is None:
        return values, np.ones(len(values))
    if len(groups) != len(values):
        raise ValueError(f"groups has {len(groups)} entries for {len(values)} values")
    _, index = np.unique(np.asarray(groups), return_inverse=True)
    return np.bincount(index, weights=values), np.bincount(index).astype(float)


def bootstrap_ci(
    values: Sequence[float],
    *,
    groups: Sequence[str] | None = None,
    confidence: float = DEFAULT_CONFIDENCE,
    n_resamples: int = DEFAULT_RESAMPLES,
    seed: int = DEFAULT_SEED,
) -> Interval:
    """Percentile bootstrap of the mean; groups (source documents) are resampled whole."""
    if len(values) == 0:
        raise ValueError("no values to resample")
    if not 0.0 < confidence < 1.0:
        raise ValueError(f"confidence must be between 0 and 1, got {confidence}")
    data = np.asarray(values, dtype=float)
    sums, counts = group_totals(data, groups)
    draws = np.random.default_rng(seed).integers(0, len(sums), size=(n_resamples, len(sums)))
    means = sums[draws].sum(axis=1) / counts[draws].sum(axis=1)
    tail = (1.0 - confidence) / 2.0
    low, high = np.quantile(means, [tail, 1.0 - tail])
    return Interval(low=float(low), estimate=float(data.mean()), high=float(high))


def paired_comparison(
    baseline: Sequence[float],
    candidate: Sequence[float],
    *,
    groups: Sequence[str] | None = None,
    confidence: float = DEFAULT_CONFIDENCE,
    n_resamples: int = DEFAULT_RESAMPLES,
    seed: int = DEFAULT_SEED,
) -> PairedResult:
    """Bootstrap the per item difference; a gap whose interval contains 0 is not clear."""
    if len(baseline) != len(candidate):
        raise ValueError("paired comparison needs the same items in the same order")
    differences = np.asarray(candidate, dtype=float) - np.asarray(baseline, dtype=float)
    interval = bootstrap_ci(
        differences, groups=groups, confidence=confidence, n_resamples=n_resamples, seed=seed
    )
    if interval.low > 0:
        verdict = "candidate is better"
    elif interval.high < 0:
        verdict = "candidate is worse"
    else:
        verdict = "no clear difference"
    return PairedResult(
        mean_difference=interval.estimate,
        low=interval.low,
        high=interval.high,
        clear=verdict != "no clear difference",
        verdict=verdict,
    )
