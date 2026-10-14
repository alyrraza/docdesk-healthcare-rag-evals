"""The call layers of an eval run, in one place so the order cannot drift (AC-EVL-04)."""

from __future__ import annotations

from pathlib import Path

from docdesk.evals.budget import BudgetedClient, TokenLedger
from docdesk.evals.cache import DEFAULT_CACHE_DIR, CachedClient
from docdesk.llm.client import LLMClient
from docdesk.llm.pacer import PacedClient, Pacer


def build_llm_stack(
    client: LLMClient,
    *,
    ledger: TokenLedger,
    pacer: Pacer,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    bypass_cache: bool = False,
) -> LLMClient:
    """Cache outermost, then budget guard, then pacer, then the real client.

    A cache hit returns before the guard and the pacer, so it costs no budget and no wait.
    """
    paced = PacedClient(client, pacer)
    budgeted = BudgetedClient(paced, ledger)
    return CachedClient(budgeted, cache_dir, bypass=bypass_cache)
