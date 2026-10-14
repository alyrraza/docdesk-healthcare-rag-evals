"""Response model for POST /retrieve: the ranked chunks a question finds, nothing generated."""

from __future__ import annotations

from pydantic import BaseModel

from docdesk.retrieval.types import RetrievalResult


class ChunkOut(BaseModel):
    """One retrieved chunk with the score the ranking gave it."""

    chunk_id: str
    document_id: str
    document_title: str
    text: str
    score: float
    page: int | None


class RetrieveOut(BaseModel):
    """The ranked chunks and the retrieval setup that produced them."""

    config_id: str
    chunks: list[ChunkOut]

    @classmethod
    def from_result(cls, result: RetrievalResult) -> RetrieveOut:
        """Convert the internal result to the public shape, without per-stage timings."""
        return cls(
            config_id=result.config_id,
            chunks=[
                ChunkOut(
                    chunk_id=str(c.chunk_id),
                    document_id=str(c.document_id),
                    document_title=c.document_title,
                    text=c.text,
                    score=c.score,
                    page=c.page,
                )
                for c in result.chunks
            ],
        )
