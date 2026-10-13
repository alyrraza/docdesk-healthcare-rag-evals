"""Slot budgets from CONTEXT.md (AC-CTX-01)."""

from __future__ import annotations

import pytest

from docdesk.context.budget import ContextBudget


def test_ac_ctx_01_the_default_slots_are_the_starting_values_from_the_design() -> None:
    budget = ContextBudget()
    assert (budget.total, budget.system, budget.schema, budget.evidence) == (6000, 500, 300, 4200)
    assert (budget.history, budget.question, budget.reserve) == (0, 300, 700)


def test_ac_ctx_01_the_slots_add_up_to_the_total() -> None:
    budget = ContextBudget()
    slots = budget.system + budget.schema + budget.evidence + budget.history
    assert slots + budget.question + budget.reserve == budget.total


def test_ac_ctx_01_slots_that_do_not_add_up_are_refused() -> None:
    with pytest.raises(ValueError, match="6000"):
        ContextBudget(evidence=5000)


def test_ac_ctx_01_a_larger_evidence_slot_can_be_chosen_if_the_others_shrink() -> None:
    budget = ContextBudget(evidence=4700, reserve=200)
    assert budget.evidence == 4700
