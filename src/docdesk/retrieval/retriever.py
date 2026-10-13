"""Runs the retrieval stages a config asks for and times each one."""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from typing import Protocol, TypeVar

import numpy as np
from sqlalchemy.orm import Session

from docdesk.retrieval.dense import dense_search
from docdesk.retrieval.fusion import reciprocal_rank_fusion
from docdesk.retrieval.keyword import keyword_search
from docdesk.retrieval.types import RetrievalConfig, RetrievalResult, ScoredChunk

T = TypeVar("T")


class QueryEncoder(Protocol):
    """The part of the embedding model retrieval needs, so tests can pass a fake."""

    def encode(self, texts: list[str]) -> np.ndarray:
        """Return one vector per text."""
        ...


def timed(timings: dict[str, float], stage: str, work: Callable[[], T]) -> T:
    """Run one stage and record its milliseconds, so the trace shows where time went."""
    started = time.perf_counter()
    result = work()
    timings[stage] = (time.perf_counter() - started) * 1000.0
    return result


def retrieve(
    session: Session,
    encoder: QueryEncoder,
    question: str,
    user_id: uuid.UUID,
    config: RetrievalConfig,
) -> RetrievalResult:
    """Return the top-k chunks for a question using only the stages the config enables."""
    started = time.perf_counter()
    timings: dict[str, float] = {}
    dense: list[ScoredChunk] = []
    keyword: list[ScoredChunk] = []
    if config.mode in ("dense", "hybrid"):
        vector = timed(timings, "embed", lambda: encoder.encode([question])[0])
        dense = timed(
            timings, "dense", lambda: dense_search(session, vector, user_id, config.top_n)
        )
    if config.mode in ("keyword", "hybrid"):
        keyword = timed(
            timings, "keyword", lambda: keyword_search(session, question, user_id, config.top_n)
        )
    if config.mode == "hybrid":
        ranked = timed(
            timings, "fuse", lambda: reciprocal_rank_fusion([dense, keyword], config.rrf_k)
        )
    else:
        ranked = dense or keyword
    timings["total"] = (time.perf_counter() - started) * 1000.0
    return RetrievalResult(ranked[: config.top_k], config.config_id, timings)
