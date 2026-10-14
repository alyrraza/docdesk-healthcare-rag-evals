"""Daily token guard and resume state, so a long eval run stops cleanly and continues later."""

from __future__ import annotations

import json
import os
import re
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from docdesk.llm.client import LLMClient, LLMRequest, LLMResult
from docdesk.llm.pacer import estimate_tokens

WINDOW_SECONDS = 24 * 3600.0
# Stop at 85 percent of the documented daily limit, to leave room for retries and other tools.
GUARD_FRACTION = 0.85
SAFE_ID = re.compile(r"[A-Za-z0-9._-]+")


class BudgetStop(Exception):
    """Raised before a call that would pass the guard; the runner saves progress and exits."""

    def __init__(self, message: str, resume_at: float | None = None) -> None:
        super().__init__(message)
        self.resume_at = resume_at


class ProgressMismatch(Exception):
    """A progress file belongs to another run, so reusing it would skip the wrong items."""


def write_json(path: Path, data: object) -> None:
    """Write through a temp file so a stopped run never leaves a half written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data), encoding="utf-8")
    os.replace(temp, path)


class TokenLedger:
    """Tokens spent per model in a rolling 24 hours, kept on disk between runs."""

    def __init__(
        self,
        path: Path,
        daily_limits: dict[str, int],
        guard_fraction: float = GUARD_FRACTION,
        clock: Callable[[], float] = time.time,
    ) -> None:
        """Take the clock as an argument; wall time, because the file outlives the process."""
        self._path = path
        self._limits = daily_limits
        self._fraction = guard_fraction
        self._clock = clock

    def used(self, model: str) -> int:
        """Tokens spent on this model in the last 24 hours."""
        return sum(tokens for _, tokens in self._recent(model))

    def record(self, model: str, tokens: int) -> None:
        """Add a finished call to the ledger and save it at once."""
        data = self._load()
        entries = self._recent(model)
        entries.append((self._clock(), tokens))
        data[model] = entries
        write_json(self._path, data)

    def check(self, model: str, estimated_tokens: int) -> None:
        """Raise BudgetStop when this call could take the model past the guard."""
        limit = self._limits.get(model)
        if limit is None:
            return
        guard = int(limit * self._fraction)
        entries = self._recent(model)
        used = sum(tokens for _, tokens in entries)
        if used + estimated_tokens <= guard:
            return
        if not entries:
            raise BudgetStop(
                f"One call to {model} may need {estimated_tokens} tokens, more than the guard "
                f"of {guard}. Lower the output allowance or raise the limit."
            )
        resume_at = self._resume_time(entries, used, estimated_tokens, guard)
        when = datetime.fromtimestamp(resume_at, tz=UTC).strftime("%Y-%m-%d %H:%M UTC")
        raise BudgetStop(
            f"Daily token guard for {model}: {used} used of {guard} allowed "
            f"(85 percent of {limit}). Progress is saved. To continue, run the same command again "
            f"after {when}; finished items are skipped.",
            resume_at,
        )

    def _resume_time(
        self, entries: list[tuple[float, int]], used: int, needed: int, guard: int
    ) -> float:
        """When enough old spend leaves the 24 hour window for the call to fit."""
        for stamp, tokens in entries:
            used -= tokens
            if used + needed <= guard:
                return stamp + WINDOW_SECONDS
        return entries[-1][0] + WINDOW_SECONDS

    def _recent(self, model: str) -> list[tuple[float, int]]:
        """Entries of the last 24 hours for one model, oldest first."""
        cutoff = self._clock() - WINDOW_SECONDS
        return [(float(t), int(n)) for t, n in self._load().get(model, []) if t > cutoff]

    def _load(self) -> dict[str, list[list[float]]]:
        """Read the ledger file; a missing file is an empty ledger."""
        if not self._path.exists():
            return {}
        return json.loads(self._path.read_text(encoding="utf-8"))


class BudgetedClient:
    """Wraps a client that calls the model. Put the cache outside it, so hits cost nothing."""

    def __init__(self, inner: LLMClient, ledger: TokenLedger) -> None:
        """Hold the client to wrap and the ledger shared by every client of the same key."""
        self._inner = inner
        self._ledger = ledger

    def complete(self, request: LLMRequest) -> LLMResult:
        """Check the guard first, call, then add the real tokens to the ledger."""
        self._ledger.check(request.model, estimate_tokens(request))
        result = self._inner.complete(request)
        self._ledger.record(request.model, result.tokens_in + result.tokens_out)
        return result


class RunProgress:
    """Item ids a run has finished, saved after each one, so a stopped run never repeats work."""

    def __init__(self, path: Path, config_id: str, bundle_id: str, done: list[str]) -> None:
        """Use RunProgress.open, which loads or creates the file."""
        self._path = path
        self._config_id = config_id
        self._bundle_id = bundle_id
        self._done = done

    @classmethod
    def open(cls, directory: Path, config_id: str, bundle_id: str) -> RunProgress:
        """Load the progress of this config and bundle, or start empty."""
        for name in (config_id, bundle_id):
            if not SAFE_ID.fullmatch(name):
                raise ValueError(f"unsafe id for a progress file name: {name!r}")
        path = directory / f"{config_id}__{bundle_id}.json"
        if not path.exists():
            return cls(path, config_id, bundle_id, [])
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("config_id") != config_id or data.get("bundle_id") != bundle_id:
            raise ProgressMismatch(f"{path.name} belongs to another config or bundle")
        return cls(path, config_id, bundle_id, list(data["done"]))

    @property
    def done_count(self) -> int:
        """How many items are finished."""
        return len(self._done)

    def is_done(self, item_id: str) -> bool:
        """Whether the runner may skip this item."""
        return item_id in self._done

    def mark_done(self, item_id: str) -> None:
        """Save the item as finished; marking it twice changes nothing."""
        if item_id in self._done:
            return
        self._done.append(item_id)
        write_json(
            self._path,
            {"config_id": self._config_id, "bundle_id": self._bundle_id, "done": self._done},
        )
