"""Deterministic failure labels (AC-EVL-03): one label per failed item, first match wins.

Judges only supply claim and key point labels; this file decides from numbers and ids. The order
follows root cause first: retrieval, then ranking, then the packer, then what the model did.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence, Set
from dataclasses import dataclass

from docdesk.evals.outcome import Behavior, Cell, Outcome, outcome_cell

# An answer passes only when every claim is supported and every key point is covered.
FAITHFUL_AT = 1.0
CORRECT_AT = 1.0


@dataclass(frozen=True)
class LabelInput:
    """Everything the labeler looks at for one item; ids are chunk ids as strings."""

    behavior: Behavior
    outcome: Outcome
    # False when the policy refusal answered before retrieval; retrieval labels then do not apply.
    retrieval_ran: bool
    # False when the answer flow abstained before packing; the packer is then not to blame.
    packed: bool
    gold_sets: Sequence[Set[str]]
    candidate_ids: Sequence[str]
    retrieved_ids: Sequence[str]
    used_ids: Sequence[str]
    faithfulness: float | None = None
    correctness: float | None = None
    contradicted: int = 0


def answer_quality_failed(item: LabelInput) -> tuple[bool, bool]:
    """Whether the judged scores say unfaithful, and whether they say incorrect."""
    unfaithful = item.faithfulness is not None and item.faithfulness < FAITHFUL_AT
    incorrect = item.contradicted > 0 or (
        item.correctness is not None and item.correctness < CORRECT_AT
    )
    return unfaithful, incorrect


def is_failed(item: LabelInput, cell: Cell) -> bool:
    """A wrong outcome fails the item; a right answer also needs good judged scores."""
    if cell != "correct_answer":
        return not cell.startswith("correct_")
    return any(answer_quality_failed(item))


def missing_from(item: LabelInput, found: Sequence[str]) -> bool:
    """True when some required evidence entry has no gold chunk in the given ids."""
    return any(not (gold & set(found)) for gold in item.gold_sets)


def wants_retrieval_label(item: LabelInput, cell: Cell) -> bool:
    """Retrieval and context labels apply to an item that should be answered and was retrieved."""
    return (
        item.behavior == "answer"
        and item.retrieval_ran
        and bool(item.gold_sets)
        and cell != "error"
    )


def retrieval_miss(item: LabelInput, cell: Cell) -> bool:
    """Some required evidence is not even among the top_n candidates."""
    return wants_retrieval_label(item, cell) and missing_from(item, item.candidate_ids)


def ranking_miss(item: LabelInput, cell: Cell) -> bool:
    """All evidence is a candidate, but some of it fell outside the top_k."""
    return wants_retrieval_label(item, cell) and missing_from(item, item.retrieved_ids)


def context_overflow(item: LabelInput, cell: Cell) -> bool:
    """All evidence was retrieved, but the packer left some of it out of the prompt."""
    return wants_retrieval_label(item, cell) and item.packed and missing_from(item, item.used_ids)


def context_distraction(item: LabelInput, cell: Cell) -> bool:
    """All evidence is in the prompt, but a non gold chunk sits first and the answer failed."""
    if not (wants_retrieval_label(item, cell) and item.packed and item.used_ids):
        return False
    gold = set().union(*item.gold_sets)
    return item.used_ids[0] not in gold and cell in ("wrong_abstain", "correct_answer")


def unfaithful(item: LabelInput, cell: Cell) -> bool:
    """The answer has a claim that the evidence does not support."""
    return cell == "correct_answer" and answer_quality_failed(item)[0]


def incorrect(item: LabelInput, cell: Cell) -> bool:
    """The answer misses or contradicts a reference key point."""
    return cell == "correct_answer" and answer_quality_failed(item)[1]


def is_cell(name: Cell) -> Callable[[LabelInput, Cell], bool]:
    """A rule that matches when the outcome cell is exactly this one."""
    return lambda item, cell: cell == name


RULES: tuple[tuple[str, Callable[[LabelInput, Cell], bool]], ...] = (
    ("retrieval_miss", retrieval_miss),
    ("ranking_miss", ranking_miss),
    ("context_overflow", context_overflow),
    ("context_distraction", context_distraction),
    ("wrong_abstain", is_cell("wrong_abstain")),
    ("missed_abstain", is_cell("missed_abstain")),
    ("wrong_refusal", is_cell("wrong_refusal")),
    ("missed_refusal", is_cell("missed_refusal")),
    ("unfaithful", unfaithful),
    ("incorrect", incorrect),
)
LABEL_ORDER = (*(name for name, _ in RULES), "other")


def label_failure(item: LabelInput) -> str | None:
    """None for a passing item, else the first label whose rule matches; `other` is the fallback."""
    cell = outcome_cell(item.behavior, item.outcome)
    if not is_failed(item, cell):
        return None
    for name, rule in RULES:
        if rule(item, cell):
            return name
    return "other"
