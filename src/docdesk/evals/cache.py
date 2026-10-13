"""Disk cache for model calls, so a repeated eval item costs no tokens (AC-EVL-04)."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from docdesk.llm.client import LLMClient, LLMRequest, LLMResult

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path(".cache/llm")


def cache_key(request: LLMRequest) -> str:
    """One hash of prompt, model, sampling and input, so any change is a different entry."""
    parts = {
        # The system section is the rendered prompt, so its hash identifies the prompt version.
        "prompt_hash": hashlib.sha256(request.system.encode("utf-8")).hexdigest(),
        "model": request.model,
        "temperature": request.temperature,
        "max_output_tokens": request.max_output_tokens,
        "json_mode": request.json_mode,
        "input": request.user,
    }
    canonical = json.dumps(parts, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class CachedClient:
    """Wraps any client; a hit returns the stored result, a miss calls the model and stores it."""

    def __init__(
        self, inner: LLMClient, directory: Path = DEFAULT_CACHE_DIR, bypass: bool = False
    ) -> None:
        """Set bypass for latency runs, which must never read or write the cache."""
        self._inner = inner
        self._directory = directory
        self._bypass = bypass

    def complete(self, request: LLMRequest) -> LLMResult:
        """Return the cached result when there is one, else call the model and keep the result."""
        if self._bypass:
            return self._inner.complete(request)
        path = self._directory / f"{cache_key(request)}.json"
        cached = self._read(path)
        if cached is not None:
            return replace(cached, cache_hit=True)
        result = self._inner.complete(request)
        self._write(path, result)
        return result

    @staticmethod
    def _read(path: Path) -> LLMResult | None:
        """Load an entry; a damaged file is logged and treated as a miss so it gets replaced."""
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return LLMResult(**{**data, "cost_usd": Decimal(data["cost_usd"]), "cache_hit": False})
        except (ValueError, KeyError, TypeError) as error:
            logger.warning("cache entry %s is unreadable (%s), calling the model", path.name, error)
            return None

    def _write(self, path: Path, result: LLMResult) -> None:
        """Write through a temp file so a stopped run never leaves half an entry."""
        self._directory.mkdir(parents=True, exist_ok=True)
        data = {
            "text": result.text,
            "tokens_in": result.tokens_in,
            "tokens_out": result.tokens_out,
            "latency_ms": result.latency_ms,
            "finish_reason": result.finish_reason,
            "model": result.model,
            "cost_usd": str(result.cost_usd),
        }
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(data), encoding="utf-8")
        os.replace(temp, path)
