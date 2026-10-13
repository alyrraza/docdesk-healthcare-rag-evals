"""The three validation layers for a model answer, in the order OUTPUTS.md describes."""

from __future__ import annotations

import re
from collections.abc import Collection, Mapping

from pydantic import ValidationError

from docdesk.generation.schema import ABSTAIN_SENTENCE, AnswerOutput
from docdesk.guardrails.citations import check_citations
from docdesk.guardrails.errors import OutputError

NUMBER = re.compile(r"\d+(?:\.\d+)?")


def parse_answer(raw: str) -> AnswerOutput:
    """Layer 1: the text must be JSON that fits the schema, with no guessing at the fields."""
    try:
        return AnswerOutput.model_validate_json(raw)
    except ValidationError as error:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in e['loc']) or 'output'}: {e['msg']}" for e in error.errors()
        )
        raise OutputError("schema", problems[:500]) from error


def check_fields(output: AnswerOutput, allowed_labels: Collection[str]) -> None:
    """Layer 2: valid JSON can still contradict itself, or cite evidence that was never shown."""
    if output.abstained:
        if output.abstain_reason == "none":
            raise OutputError("fields", "abstained is true but abstain_reason is none")
        if output.citations:
            raise OutputError("fields", "an abstained answer must have no citations")
        if output.answer != ABSTAIN_SENTENCE:
            raise OutputError("fields", "an abstained answer must use the fixed abstain sentence")
    else:
        if output.abstain_reason != "none":
            raise OutputError("fields", "abstained is false so abstain_reason must be none")
        if not output.citations:
            raise OutputError("fields", "an answer needs at least one citation")
        if not set(output.citations) <= set(output.evidence_used):
            raise OutputError("fields", "citations must be a subset of evidence_used")
    check_citations(output, allowed_labels)


def semantic_flags(output: AnswerOutput, cited_text: Mapping[str, str]) -> list[str]:
    """Layer 3: flag numbers in the answer that the cited chunks never mention; never edit them."""
    if output.abstained:
        return []
    evidence = " ".join(cited_text.get(label, "") for label in output.citations)
    known = set(NUMBER.findall(evidence))
    return [
        f"number {number} in the answer is not in the cited evidence"
        for number in dict.fromkeys(NUMBER.findall(output.answer))
        if number not in known
    ]
