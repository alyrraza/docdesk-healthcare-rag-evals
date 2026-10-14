"""The answer flow: abstain check, pack, render, call, validate, retry once, typed fallback."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from docdesk.context.budget import ContextBudget
from docdesk.context.packer import Pack, pack
from docdesk.generation.abstain import AbstainPolicy, abstain_reason
from docdesk.generation.repair import repair_prompt
from docdesk.generation.result import AnswerResult, CallUsage, Citation, abstain_output
from docdesk.generation.schema import AnswerOutput
from docdesk.guardrails.errors import OutputError
from docdesk.guardrails.output import check_fields, parse_answer, semantic_flags
from docdesk.guardrails.policy import with_disclaimer
from docdesk.ingestion.types import TokenCounting
from docdesk.llm.client import LLMClient, LLMRequest, LLMResult
from docdesk.llm.errors import LLMError, LLMTimeoutError, RateLimitedError
from docdesk.prompts.loader import PromptFile
from docdesk.prompts.renderer import RenderedPrompt, render
from docdesk.retrieval.types import RetrievalResult

log = logging.getLogger(__name__)


@dataclass
class Attempt:
    """One model call and what the checks said about it."""

    llm: LLMResult | None = None
    output: AnswerOutput | None = None
    error: OutputError | None = None
    llm_error: LLMError | None = None


def to_request(
    rendered: RenderedPrompt,
    prompt: PromptFile,
    model: str,
    *,
    temperature: float | None = None,
    max_output_tokens: int | None = None,
) -> LLMRequest:
    """Combine the rendered text with the sampling settings of the prompt file.

    An eval config can override the two settings; None keeps what the prompt file says.
    """
    return LLMRequest(
        system=rendered.system,
        user=rendered.user,
        model=model,
        temperature=float(
            prompt.params.get("temperature", 0) if temperature is None else temperature
        ),
        max_output_tokens=int(
            prompt.params.get("max_output_tokens", 600)
            if max_output_tokens is None
            else max_output_tokens
        ),
    )


def try_once(llm: LLMClient, request: LLMRequest, evidence: Pack) -> Attempt:
    """Call the model once and run the validation layers; failures are returned, not raised."""
    try:
        result = llm.complete(request)
    except LLMError as error:
        return Attempt(llm_error=error)
    try:
        if result.finish_reason == "length":
            raise OutputError("schema", "the reply was cut off at the output token limit")
        output = parse_answer(result.text)
        check_fields(output, evidence.label_to_chunk_id().keys())
    except OutputError as error:
        return Attempt(llm=result, error=error)
    return Attempt(llm=result, output=output)


def error_code_for(error: LLMError) -> str:
    """A short stable code for the trace when the provider call itself failed."""
    if isinstance(error, LLMTimeoutError):
        return "llm_timeout"
    if isinstance(error, RateLimitedError):
        return "llm_rate_limited"
    return "llm_error"


def generate_answer(
    question: str,
    retrieval: RetrievalResult,
    *,
    llm: LLMClient,
    prompt: PromptFile,
    counter: TokenCounting,
    budget: ContextBudget,
    model: str,
    abstain_policy: AbstainPolicy,
    max_per_document: int = 2,
    temperature: float | None = None,
    max_output_tokens: int | None = None,
) -> AnswerResult:
    """Answer from the retrieved chunks, or abstain; never raises for a model problem."""
    reason = abstain_reason(retrieval, abstain_policy)
    if reason:
        return finish(AnswerResult("", abstain_output(reason)))
    started = time.perf_counter()
    evidence = pack(retrieval.chunks, budget.evidence, counter, max_per_document=max_per_document)
    result = AnswerResult("", abstain_output("no_evidence"))
    result.used_ids, result.dropped_ids = evidence.used_ids, evidence.dropped_ids
    result.stage_ms["pack"] = (time.perf_counter() - started) * 1000.0
    if not evidence.items:
        return finish(result)

    variables = {"evidence": evidence.evidence_text, "question": question}
    started = time.perf_counter()
    sampling = {"temperature": temperature, "max_output_tokens": max_output_tokens}
    request = to_request(render(prompt, variables), prompt, model, **sampling)
    first = try_once(llm, request, evidence)
    attempts = [first]
    if first.error is not None:
        assert first.llm is not None
        retry = repair_prompt(prompt, variables, first.llm.text, first.error)
        attempts.append(try_once(llm, to_request(retry, prompt, model, **sampling), evidence))
        result.retry_used = True
    result.stage_ms["generate"] = (time.perf_counter() - started) * 1000.0
    account(result, attempts)
    last = attempts[-1]
    if last.output is None:
        return finish(fallback(result, last))
    result.output = last.output
    result.citations = [citation(evidence, label) for label in last.output.citations]
    result.flags = semantic_flags(last.output, {i.label: i.chunk.text for i in evidence.items})
    return finish(result)


def account(result: AnswerResult, attempts: list[Attempt]) -> None:
    """Add up tokens, cost and calls over every attempt, so a retry is visible in the cost."""
    for attempt in attempts:
        if attempt.llm is None:
            continue
        result.llm_calls += 1
        llm = attempt.llm
        result.calls.append(
            CallUsage(
                llm.model, llm.tokens_in, llm.tokens_out, llm.cost_usd, llm.cache_hit, llm.slot
            )
        )
        result.tokens_in += attempt.llm.tokens_in
        result.tokens_out += attempt.llm.tokens_out
        result.cost_usd += attempt.llm.cost_usd
        result.model = attempt.llm.model
        result.finish_reason = attempt.llm.finish_reason
    result.llm_calls += sum(1 for a in attempts if a.llm_error is not None)


def fallback(result: AnswerResult, last: Attempt) -> AnswerResult:
    """Return the typed system_error answer and keep the raw reply for review."""
    result.output = abstain_output("system_error")
    result.citations = []
    if last.llm_error is not None:
        result.error_code = error_code_for(last.llm_error)
        log.warning("model call failed: %s: %s", type(last.llm_error).__name__, last.llm_error)
    else:
        result.error_code = "output_invalid"
        result.raw_output = last.llm.text if last.llm else None
        log.warning("model output failed validation twice: %s", last.error)
    return result


def citation(evidence: Pack, label: str) -> Citation:
    """Look up the chunk behind a label the model cited."""
    chunk = next(item.chunk for item in evidence.items if item.label == label)
    return Citation(
        label, chunk.chunk_id, chunk.document_id, chunk.document_title, chunk.text, chunk.page
    )


def finish(result: AnswerResult) -> AnswerResult:
    """Put the disclaimer on the final text; the one place it is added (AC-GEN-06)."""
    result.answer = with_disclaimer(result.output.answer)
    return result
