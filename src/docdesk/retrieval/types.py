"""Plain data shared by every retrieval stage."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Literal

Mode = Literal["dense", "keyword", "hybrid"]


@dataclass(frozen=True)
class ScoredChunk:
    """One retrieved chunk with the text and title the answer and its citations need."""

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    text: str
    score: float
    # Which leg found it: "dense", "keyword" or "both" after fusion.
    source: str
    page: int | None = None


@dataclass(frozen=True)
class RetrievalConfig:
    """The settings of one retrieval setup; its id is stored on every trace and eval run."""

    mode: Mode = "hybrid"
    top_n: int = 20
    top_k: int = 5
    rrf_k: int = 60

    @property
    def config_id(self) -> str:
        """A readable id that changes whenever any setting changes."""
        return f"{self.mode}-n{self.top_n}-k{self.top_k}-rrf{self.rrf_k}"


@dataclass(frozen=True)
class RetrievalResult:
    """Ranked chunks plus per-stage milliseconds for the trace."""

    chunks: list[ScoredChunk]
    config_id: str
    timings_ms: dict[str, float] = field(default_factory=dict)

    @property
    def best_score(self) -> float:
        """The top score, which generation compares with the abstain threshold (AC-GEN-03)."""
        return self.chunks[0].score if self.chunks else 0.0
