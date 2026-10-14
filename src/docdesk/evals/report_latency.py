"""p50 and p95 of per item stage latency, from non cached calls only (F4)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from docdesk.evals.report_table import table

if TYPE_CHECKING:  # report_data imports this file, so the import is for type checkers only
    from docdesk.evals.report_data import ResultRecord

STAGES = ("retrieval_ms", "generation_ms", "judge_ms", "total_ms")
# Retrieval never goes through the LLM cache, so its time is real even when a model call was cached.
ALWAYS_REAL = ("retrieval_ms",)


@dataclass(frozen=True)
class Percentiles:
    """Median and 95th percentile in milliseconds, and how many items they rest on."""

    n: int
    p50: float
    p95: float


def latency_stats(records: list[ResultRecord]) -> dict[str, Percentiles]:
    """Per stage percentiles; an item with any cached model call is left out of the model stages.

    Empty when no item has stored latency (a run from before migration 0017): never zeros.
    """
    stored = [r.latency for r in records if r.latency]
    found: dict[str, Percentiles] = {}
    for stage in STAGES:
        real = [
            lat[stage]
            for lat in stored
            if lat.get(stage) is not None and (stage in ALWAYS_REAL or not lat.get("cache_hit"))
        ]
        if real:
            p50, p95 = np.percentile(real, [50, 95])
            found[stage] = Percentiles(len(real), float(p50), float(p95))
    return found


def latency_lines(records: list[ResultRecord]) -> list[str]:
    """The report section; says plainly when nothing was recorded."""
    stats = latency_stats(records)
    if not stats:
        return [
            "## Latency", "",
            "Latency: not recorded for this run (it was stored before per item timings existed, "
            "and old runs are not backfilled).", "",
        ]
    rows = [
        [stage.removesuffix("_ms"), str(s.n), f"{s.p50:.0f}", f"{s.p95:.0f}"]
        for stage, s in stats.items()
    ]
    return [
        "## Latency (non cached calls only)", "",
        "Milliseconds per item. An item with any cached model call is left out of the generation, "
        "judge and total rows, because a cache hit has no real latency. Retrieval is never cached. "
        "Retrieval time includes the network round trip to the hosted database.", "",
        *table(["stage", "items", "p50 ms", "p95 ms"], rows), "",
    ]
