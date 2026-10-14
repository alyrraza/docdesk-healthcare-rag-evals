"""The golden item schema (AC-EVL-01): what a hand verified question must carry."""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_QUOTE_CHARS = 300
SOURCE_KEY = re.compile(r"seed:[a-z]+:\S+")

ItemType = Literal[
    "single_fact", "multi_chunk", "structured", "mixed", "unanswerable", "adversarial"
]
Route = Literal["documents", "structured", "both"]
AdversarialKind = Literal["none", "injected_instruction", "diagnosis_request", "dose_request"]
ANSWERABLE_TYPES = ("single_fact", "multi_chunk", "structured", "mixed")
EXPECTED_ROUTE = {
    "single_fact": "documents",
    "multi_chunk": "documents",
    "structured": "structured",
    "mixed": "both",
}


class Evidence(BaseModel):
    """A verbatim quote from one corpus document, which survives any change of chunking."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source: str
    text: str = Field(min_length=1, max_length=MAX_QUOTE_CHARS)
    alt_sources: list[str] = []

    @field_validator("source")
    @classmethod
    def must_be_a_document_key(cls, value: str) -> str:
        """Accept only the stable per document key, never a database id."""
        if not SOURCE_KEY.fullmatch(value):
            raise ValueError("source must look like seed:<corpus>:<source id>")
        return value

    @model_validator(mode="after")
    def alternates_are_other_documents(self) -> Evidence:
        """Alternates are other documents with the same words, each given by its stable key."""
        for key in self.alt_sources:
            if not SOURCE_KEY.fullmatch(key):
                raise ValueError("alt_sources must look like seed:<corpus>:<source id>")
        if self.source in self.alt_sources or len(set(self.alt_sources)) != len(self.alt_sources):
            raise ValueError("alt_sources must be other documents, each listed once")
        return self

    @field_validator("text")
    @classmethod
    def no_edge_whitespace(cls, value: str) -> str:
        """Keep quotes trimmed so they match the cleaned document text exactly."""
        if value != value.strip():
            raise ValueError("a quote must not start or end with whitespace")
        return value


class GoldenItem(BaseModel):
    """One question with the facts and evidence a correct answer needs."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^gi-\d{3}$")
    type: ItemType
    split: Literal["dev", "test"]
    question: str = Field(min_length=10)
    answerable: bool
    gold_route: Route
    gold_facts: list[str] = []
    gold_evidence: list[Evidence] = []
    no_evidence_reason: str = ""
    gold_sql: str | None = None
    gold_result: list[Any] | None = None
    adversarial_kind: AdversarialKind = "none"
    verified: bool = False
    verified_by: str | None = Field(default=None, min_length=1)
    verified_on: date | None = None

    @model_validator(mode="after")
    def check_the_rules_between_fields(self) -> GoldenItem:
        """Collect rules that need several fields, so one error names what to fix."""
        problems = [
            *self.answer_problems(),
            *self.evidence_problems(),
            *self.sql_problems(),
            *self.verification_problems(),
        ]
        if problems:
            raise ValueError("; ".join(problems))
        return self

    def answer_problems(self) -> list[str]:
        """Rules tying type, answerable, facts and adversarial_kind together."""
        problems = []
        if self.type in ANSWERABLE_TYPES and not self.answerable:
            problems.append(f"a {self.type} item must be answerable")
        if self.type == "unanswerable" and self.answerable:
            problems.append("an unanswerable item must have answerable false")
        if self.answerable and not self.gold_facts:
            problems.append("an answerable item needs gold_facts")
        if not self.answerable and (self.gold_facts or self.gold_evidence):
            problems.append("an unanswerable item has no gold_facts and no gold_evidence")
        if (self.type == "adversarial") != (self.adversarial_kind != "none"):
            problems.append("adversarial_kind must be set exactly when the type is adversarial")
        expected = EXPECTED_ROUTE.get(self.type)
        if expected and self.gold_route != expected:
            problems.append(f"a {self.type} item has gold_route {expected}")
        return problems

    def evidence_problems(self) -> list[str]:
        """Rules for the quotes and for the reason an item may have none."""
        problems = []
        count = len(self.gold_evidence)
        wants_quotes = self.answerable and self.gold_route in ("documents", "both")
        if wants_quotes and count == 0:
            problems.append("a document item needs gold_evidence")
        if self.type == "single_fact" and count > 1:
            problems.append("a single_fact item has exactly one quote")
        if self.type == "multi_chunk" and count < 2:
            problems.append("a multi_chunk item needs at least two quotes")
        if len({(e.source, e.text) for e in self.gold_evidence}) != count:
            problems.append("duplicate quote in gold_evidence")
        if not self.answerable and not self.no_evidence_reason.strip():
            problems.append("an item without evidence needs a no_evidence_reason")
        if count and self.no_evidence_reason:
            problems.append("no_evidence_reason is only for items without gold_evidence")
        return problems

    def sql_problems(self) -> list[str]:
        """Structured and mixed items carry the query and its result; others must not."""
        has_sql = self.gold_sql is not None or self.gold_result is not None
        if self.gold_route == "documents" or not self.answerable:
            wrong = "gold_sql and gold_result are only for structured or mixed items"
            return [wrong] if has_sql else []
        if not self.gold_sql or self.gold_result is None:
            return ["a structured or mixed item needs gold_sql and gold_result"]
        return []

    def verification_problems(self) -> list[str]:
        """A verified item says who checked it and when; a draft needs neither."""
        if self.verified and (self.verified_by is None or self.verified_on is None):
            return ["a verified item needs verified_by and verified_on"]
        return []
