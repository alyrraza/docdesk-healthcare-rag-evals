"""Request and response models for POST /query."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from docdesk.generation.result import AnswerResult
from docdesk.guardrails.policy import DISCLAIMER

# About 250 tokens, inside the 300 token question slot of the context budget (AC-GRD-02).
MAX_QUESTION_CHARS = 1000


class QueryRequest(BaseModel):
    """A single question; there is no conversation history in v2."""

    question: str = Field(max_length=MAX_QUESTION_CHARS)

    @field_validator("question")
    @classmethod
    def not_blank(cls, value: str) -> str:
        """Reject a question that is only whitespace, which would waste a model call."""
        if not value.strip():
            raise ValueError("question must not be blank")
        return value.strip()


class CitationOut(BaseModel):
    """One cited chunk with what a reader needs to check the claim."""

    label: str
    chunk_id: str
    document_id: str
    document_title: str
    text: str
    page: int | None


class QueryOut(BaseModel):
    """The answer without the disclaimer text mixed in, plus the disclaimer as its own field."""

    answer: str
    disclaimer: str
    confidence: str
    abstained: bool
    abstain_reason: str
    citations: list[CitationOut]

    @classmethod
    def from_result(cls, result: AnswerResult) -> QueryOut:
        """Convert the internal result to the public shape, without costs or error codes."""
        return cls(
            answer=result.output.answer,
            disclaimer=DISCLAIMER,
            confidence=result.output.confidence,
            abstained=result.abstained,
            abstain_reason=result.output.abstain_reason,
            citations=[
                CitationOut(
                    label=c.label,
                    chunk_id=str(c.chunk_id),
                    document_id=str(c.document_id),
                    document_title=c.document_title,
                    text=c.text,
                    page=c.page,
                )
                for c in result.citations
            ],
        )
