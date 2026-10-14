"""Tokens and cost per model for ONE run, added up from the per call usage stored on its rows.

T098b: the earlier version summed the whole cache folder, so runs were mixed. Each stored entry
says which role made the call, which model, and whether the cache answered it. A cache hit costs
nothing this run, so its tokens count as saved, not billed.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # report_data imports this file, so the import is for type checkers only
    from docdesk.evals.report_data import ResultRecord


@dataclass(frozen=True)
class ModelUsage:
    """Calls, tokens and list price cost of one model in one run."""

    model: str
    calls: int
    cached_calls: int
    tokens_billed: int
    tokens_saved: int
    cost_usd: Decimal
    cost_billed: Decimal


def usage_from_records(records: list[ResultRecord]) -> list[ModelUsage] | None:
    """Per model usage of a run, or None when any item that ran has no stored usage.

    None means the run was stored before per call usage existed. It is never estimated.
    """
    ran = [r for r in records if r.metrics.get("status") == "ok"]
    if any(r.usage is None for r in ran):
        return None
    totals: dict[str, list] = defaultdict(lambda: [0, 0, 0, 0, Decimal(0), Decimal(0)])
    for record in ran:
        for call in record.usage or []:
            row = totals[call["model"]]
            tokens, cost = call["tokens_in"] + call["tokens_out"], Decimal(call["cost_usd"])
            row[0] += 1
            row[4] += cost
            if call["cache_hit"]:
                row[1] += 1
                row[3] += tokens
            else:
                row[2] += tokens
                row[5] += cost
    return [ModelUsage(m, int(v[0]), int(v[1]), int(v[2]), int(v[3]), Decimal(v[4]), Decimal(v[5]))
            for m, v in sorted(totals.items())]
