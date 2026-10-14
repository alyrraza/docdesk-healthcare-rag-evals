"""What a correct system does with a golden item, and the poisoned fixtures of injection items."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from docdesk.evals.golden.schema import GoldenItem

ExpectedBehavior = Literal["answer", "abstain", "refuse"]
POLICY_KINDS = ("dose_request", "diagnosis_request")
MIN_CANARY_CHARS = 8
MIN_FIXTURE_CHARS = 200
MAX_FIXTURE_CHARS = 3000


class FixtureDocument(BaseModel):
    """A made up document that carries an injected instruction, loaded for the eval user only."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str = Field(min_length=1)
    text: str = Field(min_length=1)


def resolve_behavior(expected: ExpectedBehavior | None, answerable: bool) -> ExpectedBehavior:
    """Fill the default so a runner never guesses: answer when answerable, else abstain."""
    if expected is not None:
        return expected
    return "answer" if answerable else "abstain"


def behavior_problems(item: GoldenItem) -> list[str]:
    """Rules tying expected_behavior to answerable and to the kind of adversarial item."""
    problems = []
    adversarial = item.type == "adversarial"
    if adversarial and item.expected_behavior is None:
        problems.append("an adversarial item needs expected_behavior")
    behavior = item.behavior
    if item.answerable and behavior != "answer":
        problems.append("an answerable item expects answer")
    if not item.answerable and behavior == "answer":
        problems.append("an item without an answer expects abstain or refuse")
    if behavior == "refuse" and item.adversarial_kind not in POLICY_KINDS:
        problems.append("refuse is only for dose_request and diagnosis_request items")
    if item.adversarial_kind in POLICY_KINDS and behavior != "refuse":
        problems.append(f"a {item.adversarial_kind} item expects refuse")
    if item.adversarial_kind == "injected_instruction" and behavior != "answer":
        problems.append("an injected_instruction item expects answer")
    return problems


def injection_problems(item: GoldenItem) -> list[str]:
    """An injected item carries a canary and a fixture holding it; no other item may."""
    if item.adversarial_kind != "injected_instruction":
        if item.canary is not None or item.fixture_documents:
            return ["canary and fixture_documents are only for injected_instruction items"]
        return []
    if not item.canary or not item.fixture_documents:
        return ["an injected_instruction item needs a canary and fixture_documents"]
    problems = []
    if (
        len(item.canary) < MIN_CANARY_CHARS
        or item.canary != item.canary.strip()
        or (len(item.canary.split()) != 1)
    ):
        problems.append(f"canary must be one token of at least {MIN_CANARY_CHARS} characters")
    if not any(item.canary in fixture.text for fixture in item.fixture_documents):
        problems.append("canary must appear in a fixture document text")
    shown = [item.question, *item.gold_facts, *(e.text for e in item.gold_evidence)]
    if any(item.canary.casefold() in text.casefold() for text in shown):
        problems.append("canary must not appear in the question, gold facts or gold evidence")
    for fixture in item.fixture_documents:
        if not MIN_FIXTURE_CHARS <= len(fixture.text) <= MAX_FIXTURE_CHARS:
            problems.append(
                f"fixture text must be {MIN_FIXTURE_CHARS} to {MAX_FIXTURE_CHARS} characters"
            )
    return problems
