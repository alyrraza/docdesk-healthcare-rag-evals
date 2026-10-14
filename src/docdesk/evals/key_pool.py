"""Several provider keys behind one client: use the first slot with room, rotate at its limit."""

from __future__ import annotations

import json
import logging
from dataclasses import replace
from pathlib import Path

from docdesk.evals.budget import BudgetStop, TokenLedger, write_json
from docdesk.llm.client import LLMClient, LLMRequest, LLMResult
from docdesk.llm.errors import RateLimitedError
from docdesk.llm.pacer import estimate_tokens

logger = logging.getLogger(__name__)


def slot_key(model: str, slot: int) -> str:
    """Ledger name of one model on one key slot (slots count from 1)."""
    return f"{model}#slot{slot}"


def seed_pool_ledger(pool_path: Path, old_path: Path) -> None:
    """Why: tokens already spent before the pool existed all went through slot 1, so they count.

    Does nothing when the pool ledger exists, so a restart never counts the same spend twice.
    """
    if pool_path.exists() or not old_path.exists():
        return
    old = json.loads(old_path.read_text(encoding="utf-8"))
    write_json(pool_path, {slot_key(model, 1): entries for model, entries in old.items()})


class KeyPoolClient:
    """Sends each call with the first slot that still has room; the request is never changed."""

    def __init__(self, clients: list[LLMClient], ledger: TokenLedger) -> None:
        """Hold one client per key slot (index 0 is slot 1) and the per slot ledger."""
        self._clients = clients
        self._ledger = ledger
        # Slots the provider itself said are out of daily tokens, for this process.
        self._exhausted: set[tuple[str, int]] = set()

    def complete(self, request: LLMRequest) -> LLMResult:
        """Try slots in order; raise BudgetStop when none has room, so the run stops cleanly."""
        estimate = estimate_tokens(request)
        stops: list[BudgetStop] = []
        for slot, client in enumerate(self._clients, start=1):
            if (request.model, slot) in self._exhausted:
                continue
            key = slot_key(request.model, slot)
            try:
                self._ledger.check(key, estimate)
            except BudgetStop as stop:
                logger.info("slot %d is at its daily guard for %s", slot, request.model)
                stops.append(stop)
                continue
            try:
                result = client.complete(request)
            except RateLimitedError as error:
                if not error.daily:
                    raise
                logger.warning("slot %d hit the provider daily limit for %s", slot, request.model)
                self._exhausted.add((request.model, slot))
                continue
            self._ledger.record(key, result.tokens_in + result.tokens_out)
            logger.info("slot %d served a %s call", slot, request.model)
            return replace(result, slot=slot)
        resumes = [s.resume_at for s in stops if s.resume_at is not None]
        raise BudgetStop(
            f"Every key slot is out of daily tokens for {request.model} "
            f"({len(self._clients)} slots). Progress is saved. Run the same command again later; "
            "finished items are skipped.",
            min(resumes) if resumes else None,
        )
