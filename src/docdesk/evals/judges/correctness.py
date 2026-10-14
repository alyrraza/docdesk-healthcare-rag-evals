"""Correctness judge (T091): the judge labels reference key points, this code computes the score.

Extra information is never penalised: the judge has no label for it, so only a missing key point
or a contradiction lowers the score (rubric rule in docs/modules/evals.md).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

from docdesk.evals.judges.call import NO_USAGE, JudgeUsage, call_judge
from docdesk.evals.judges.parser import JudgeParser
from docdesk.evals.judges.schemas import CorrectnessJudgement, KeyPointLabel
from docdesk.llm.client import LLMClient
from docdesk.prompts.loader import PromptFile

Status = Literal["scored", "decided_by_code", "skipped", "parse_failed"]


@dataclass(frozen=True)
class CorrectnessResult:
    """Labels per key point, the score, and why there is no score if there is none."""

    status: Status
    score: float | None
    labels: list[KeyPointLabel] = field(default_factory=list)
    usage: JudgeUsage = NO_USAGE

    @property
    def contradicted(self) -> int:
        """How many key points the answer contradicts, reported next to the score."""
        return sum(1 for item in self.labels if item.label == "contradicted")


def correctness_score(labels: Sequence[KeyPointLabel]) -> float | None:
    """Covered key points over all key points; None when there are none to cover."""
    if not labels:
        return None
    return sum(1 for item in labels if item.label == "covered") / len(labels)


def numbered(key_points: Sequence[str]) -> str:
    """The key points as the judge reads them, one numbered line each."""
    return "\n".join(f"{number}. {text}" for number, text in enumerate(key_points, start=1))


def labels_match(labels: Sequence[KeyPointLabel], count: int) -> bool:
    """Every key point has exactly one label, so a short or doubled reply is never scored."""
    return sorted(item.point for item in labels) == list(range(1, count + 1))


def judge_correctness(
    *,
    prompt: PromptFile,
    parser: JudgeParser[CorrectnessJudgement],
    client: LLMClient,
    model: str,
    question: str,
    answer: str,
    key_points: Sequence[str],
    answered: bool,
) -> CorrectnessResult:
    """Label how much of the reference an answer covers; unanswerable items have no key points."""
    if not key_points:
        return CorrectnessResult("skipped", None)
    if not answered or not answer.strip():
        # An abstain or empty answer covers nothing, so code decides it without a model call.
        missing = [KeyPointLabel(point=n, label="missing") for n in range(1, len(key_points) + 1)]
        return CorrectnessResult("decided_by_code", 0.0, missing)
    variables = {"question": question, "answer": answer, "key_points": numbered(key_points)}
    judgement, usage = call_judge(prompt, variables, client=client, model=model, parser=parser)
    if judgement is not None and not labels_match(judgement.key_points, len(key_points)):
        parser.reject("labels do not match the key points")
        judgement = None
    if judgement is None:
        return CorrectnessResult("parse_failed", None, usage=usage)
    labels = sorted(judgement.key_points, key=lambda item: item.point)
    return CorrectnessResult("scored", correctness_score(labels), labels, usage)
