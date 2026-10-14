"""One judge call: render, ask, parse. The client passed in already has cache and guards."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TypeVar

from pydantic import BaseModel

from docdesk.evals.judges.parser import JudgeParser
from docdesk.generation.answer import to_request
from docdesk.llm.client import LLMClient
from docdesk.prompts.loader import PromptFile
from docdesk.prompts.renderer import render

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class JudgeUsage:
    """What a judge call cost, so the report can add up tokens and money."""

    calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: Decimal = Decimal("0")
    cache_hit: bool = False
    slot: int | None = None


NO_USAGE = JudgeUsage()


def call_judge(
    prompt: PromptFile,
    variables: dict[str, str],
    *,
    client: LLMClient,
    model: str,
    parser: JudgeParser[T],
) -> tuple[T | None, JudgeUsage]:
    """Ask the judge once; a reply that does not parse comes back as None and is counted."""
    request = to_request(render(prompt, variables), prompt, model)
    result = client.complete(request)
    usage = JudgeUsage(
        calls=1,
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
        cost_usd=result.cost_usd,
        cache_hit=result.cache_hit,
        slot=result.slot,
    )
    return parser.parse(result.text), usage
