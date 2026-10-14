"""Tokens and cost per model, read from the disk cache entries (T098a).

The stored result rows only hold totals for the generator and both judges together. Each cache
entry records its own model, so adding them up gives the split. The cache has no run id, so this
counts every entry in the folder.
"""

from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelUsage:
    """Calls, tokens and list price cost of one model."""

    model: str
    calls: int
    tokens_in: int
    tokens_out: int
    cost_usd: Decimal


def usage_from_cache(directory: Path) -> list[ModelUsage]:
    """Add up the cache entries by model; a damaged entry is logged and left out."""
    calls: Counter[str] = Counter()
    tokens_in: Counter[str] = Counter()
    tokens_out: Counter[str] = Counter()
    cost: defaultdict[str, Decimal] = defaultdict(Decimal)
    for path in sorted(directory.glob("*.json")) if directory.exists() else []:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            model = str(data["model"])
            used_in, used_out, price = int(data["tokens_in"]), int(data["tokens_out"]), Decimal(
                data["cost_usd"])
        except (ValueError, KeyError, TypeError) as error:
            log.warning("cache entry %s is unreadable (%s), left out", path.name, error)
            continue
        calls[model] += 1
        tokens_in[model] += used_in
        tokens_out[model] += used_out
        cost[model] += price
    return [ModelUsage(m, calls[m], tokens_in[m], tokens_out[m], cost[m]) for m in sorted(calls)]
