"""Agreement between judge and reference labels: table, raw agreement, kappa (T100)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from docdesk.evals.stats import DEFAULT_CONFIDENCE, DEFAULT_RESAMPLES, DEFAULT_SEED

SINGLE_CLASS = "undefined, single class"
UNSTABLE_SHARE = 0.9


@dataclass(frozen=True)
class KappaInterval:
    """A percentile interval over the resamples that had a kappa, and how many those were."""

    low: float | None
    high: float | None
    valid: int
    resamples: int


def confusion(pairs: Sequence[tuple[str, str]], labels: Sequence[str]) -> list[list[int]]:
    """Why: one table (reference rows, judge columns) feeds every other number in the report."""
    index = {label: place for place, label in enumerate(labels)}
    table = [[0] * len(labels) for _ in labels]
    for reference, judge in pairs:
        table[index[reference]][index[judge]] += 1
    return table


def agreement(table: Sequence[Sequence[int]]) -> float:
    """Raw agreement: the share of pairs on the diagonal."""
    total = sum(map(sum, table))
    return sum(table[i][i] for i in range(len(table))) / total


def kappas(tables: np.ndarray) -> np.ndarray:
    """Kappa of many tables at once (shape n, k, k); NaN where either side used a single class."""
    total = tables.sum(axis=(1, 2)).astype(float)
    rows, cols = tables.sum(axis=2) / total[:, None], tables.sum(axis=1) / total[:, None]
    observed = np.trace(tables, axis1=1, axis2=2) / total
    chance = (rows * cols).sum(axis=1)
    single = ((rows > 0).sum(axis=1) < 2) | ((cols > 0).sum(axis=1) < 2)
    with np.errstate(divide="ignore", invalid="ignore"):
        value = (observed - chance) / (1 - chance)
    return np.where(single, np.nan, value)


def cohen_kappa(table: Sequence[Sequence[int]]) -> float | None:
    """Chance corrected agreement; None when the reference or the judge used only one class."""
    value = float(kappas(np.asarray([table]))[0])
    return None if np.isnan(value) else value


def majority_share(table: Sequence[Sequence[int]]) -> float:
    """The largest share one class has on either side, to warn that kappa is unstable."""
    grid = np.asarray(table, dtype=float)
    return float(max(grid.sum(axis=1).max(), grid.sum(axis=0).max()) / grid.sum())


def kappa_interval(
    pairs: Sequence[tuple[str, str]],
    groups: Sequence[int],
    labels: Sequence[str],
    *,
    resamples: int = DEFAULT_RESAMPLES,
    seed: int = DEFAULT_SEED,
    confidence: float = DEFAULT_CONFIDENCE,
) -> KappaInterval | None:
    """Bootstrap kappa, resampling whole groups (all key points of one output stay together).

    Resamples where one side has a single class have no kappa and are counted out, not forced
    into a number. None when the estimate itself is undefined.
    """
    if cohen_kappa(confusion(pairs, labels)) is None:
        return None
    ids = sorted(set(groups))
    per_group = np.zeros((len(ids), len(labels), len(labels)), dtype=int)
    index = {label: place for place, label in enumerate(labels)}
    for (reference, judge), group in zip(pairs, groups, strict=True):
        per_group[ids.index(group), index[reference], index[judge]] += 1
    draws = np.random.default_rng(seed).integers(0, len(ids), size=(resamples, len(ids)))
    values = kappas(per_group[draws].sum(axis=1))
    values = values[~np.isnan(values)]
    if len(values) == 0:
        return KappaInterval(None, None, 0, resamples)
    tail = (1.0 - confidence) / 2.0
    low, high = np.quantile(values, [tail, 1.0 - tail])
    return KappaInterval(float(low), float(high), len(values), resamples)
