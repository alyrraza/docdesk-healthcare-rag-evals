"""Reads a judge reply into a schema and counts every failure, so none is hidden."""

from __future__ import annotations

import re
from typing import Generic, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

# One fenced block, with or without the json label; a judge sometimes adds it despite JSON mode.
FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
MAX_REASON_CHARS = 200


class JudgeParser(Generic[T]):
    """One parser per judge and run; its counts feed the report as judge_error."""

    def __init__(self, schema: type[T]) -> None:
        """Hold the schema the judge must follow and start the counts at zero."""
        self._schema = schema
        self.attempts = 0
        self.failures: list[str] = []

    @property
    def failure_rate(self) -> float:
        """Share of replies that did not parse, shown next to every judge score."""
        return len(self.failures) / self.attempts if self.attempts else 0.0

    def parse(self, reply: str) -> T | None:
        """Return the parsed verdict, or None after recording why; a failure is never a pass."""
        self.attempts += 1
        body = self._unwrap(reply)
        if not body:
            return self._fail("empty reply")
        try:
            return self._schema.model_validate_json(body)
        except ValidationError as error:
            kinds = ", ".join(sorted({str(e["type"]) for e in error.errors()}))
            return self._fail(f"invalid judge json: {kinds}")

    @staticmethod
    def _unwrap(reply: str) -> str:
        """Take the content of a fenced block when there is one, else the whole reply."""
        match = FENCE.search(reply)
        return (match.group(1) if match else reply).strip()

    def _fail(self, reason: str) -> None:
        """Record a short reason; the raw reply stays out of the report."""
        self.failures.append(reason[:MAX_REASON_CHARS])
        return None
