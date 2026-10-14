"""Faithfulness judge (T090): the judge labels claims, this code computes the score."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

from docdesk.evals.judges.call import NO_USAGE, JudgeUsage, call_judge
from docdesk.evals.judges.parser import JudgeParser
from docdesk.evals.judges.schemas import ClaimLabel, FaithfulnessJudgement
from docdesk.llm.client import LLMClient
from docdesk.prompts.loader import PromptFile

Status = Literal["scored", "no_claims", "skipped", "parse_failed"]


@dataclass(frozen=True)
class FaithfulnessResult:
    """Per claim labels (for the report), the score, and why there is no score if there is none."""

    status: Status
    score: float | None
    labels: list[ClaimLabel] = field(default_factory=list)
    usage: JudgeUsage = NO_USAGE


def faithfulness_score(labels: Sequence[ClaimLabel]) -> float | None:
    """Supported claims over all claims; None for no claims, because 1.0 would reward silence."""
    if not labels:
        return None
    return sum(1 for item in labels if item.label == "supported") / len(labels)


def judge_faithfulness(
    *,
    prompt: PromptFile,
    parser: JudgeParser[FaithfulnessJudgement],
    client: LLMClient,
    model: str,
    question: str,
    answer: str,
    evidence: str,
    answered: bool,
) -> FaithfulnessResult:
    """Label the claims of an answer against the context it was written from."""
    if not answered or not answer.strip():
        # Code already decided this outcome (abstain, refuse, empty), so no tokens are spent.
        return FaithfulnessResult("skipped", None)
    variables = {"question": question, "answer": answer, "evidence": evidence}
    judgement, usage = call_judge(prompt, variables, client=client, model=model, parser=parser)
    if judgement is None:
        return FaithfulnessResult("parse_failed", None, usage=usage)
    score = faithfulness_score(judgement.claims)
    status: Status = "scored" if score is not None else "no_claims"
    return FaithfulnessResult(status, score, judgement.claims, usage)
