"""Batch 5 (T086): adversarial drafts follow the schema, the split plan and the policy filter."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from docdesk.evals.golden.loader import read_file, read_items
from docdesk.evals.golden.schema import GoldenItem
from docdesk.evals.golden.splits import split_for
from docdesk.guardrails.input import check_policy

GOLDEN = Path(__file__).resolve().parents[2] / "evals" / "golden"
# Findings, not goals: questions the pattern filter does not refuse today (AC-GEN-05). The filter
# is not changed in T086; this set changes only when a measured fix lands (see DECISIONS.md).
FILTER_MISSES = {"gi-074", "gi-077"}


def batch() -> list[GoldenItem]:
    """The items of batch 5, which must parse without problems."""
    items, problems = read_file(GOLDEN / "batch5_adversarial.yaml")
    assert problems == []
    return items


def test_ac_evl_01_batch_five_has_six_adversarial_items_split_4_dev_and_2_test() -> None:
    items = batch()
    assert {item.type for item in items} == {"adversarial"}
    assert [item.split for item in items] == [split_for("adversarial", n) for n in range(6)]
    assert Counter(item.split for item in items) == {"dev": 4, "test": 2}


def test_ac_evl_01_batch_five_ids_continue_after_gi_073() -> None:
    assert [item.id for item in batch()] == [f"gi-{n:03d}" for n in range(74, 80)]


def test_ac_evl_01_batch_five_is_two_doses_two_diagnoses_and_two_injections() -> None:
    kinds = Counter(item.adversarial_kind for item in batch())
    assert kinds == {"dose_request": 2, "diagnosis_request": 2, "injected_instruction": 2}


def test_ac_gen_05_policy_items_expect_refuse_and_injected_items_expect_answer() -> None:
    for item in batch():
        wanted = "answer" if item.adversarial_kind == "injected_instruction" else "refuse"
        assert item.behavior == wanted, item.id
        assert item.expected_behavior == wanted, item.id


def test_ac_gen_05_policy_questions_are_first_person_and_dose_requests_have_a_number() -> None:
    for item in batch():
        if item.adversarial_kind == "injected_instruction":
            continue
        words = item.question.lower().replace(",", " ").split()
        assert {"i", "my"} & set(words), item.id
        if item.adversarial_kind == "dose_request":
            assert any(char.isdigit() for char in item.question), item.id


def test_ac_evl_01_batch_five_items_are_drafts() -> None:
    for item in batch():
        assert item.verified is False
        assert item.verified_by is None


def test_ac_gen_05_the_filter_refuses_every_policy_question_except_the_known_misses() -> None:
    not_refused = {
        item.id
        for item in batch()
        if item.behavior == "refuse" and not check_policy(item.question).refused
    }
    assert not_refused == FILTER_MISSES


def test_ac_gen_05_the_filter_lets_injected_item_questions_through() -> None:
    for item in batch():
        if item.adversarial_kind == "injected_instruction":
            assert not check_policy(item.question).refused, item.id


def test_ac_grd_01_canaries_are_unique_across_the_whole_golden_set() -> None:
    items, _ = read_items(GOLDEN)
    canaries = [item.canary for _, item in items if item.canary]
    assert len(canaries) == 2
    assert len(set(canaries)) == len(canaries)


def test_ac_grd_01_each_injected_item_has_one_real_quote_and_a_fixture_on_the_same_topic() -> None:
    for item in batch():
        if item.adversarial_kind != "injected_instruction":
            assert item.gold_evidence == [] and item.fixture_documents == []
            continue
        assert len(item.gold_evidence) == 1
        topic = "allopurinol" if "allopurinol" in item.question.lower() else "colchicine"
        assert all(topic in fixture.text.lower() for fixture in item.fixture_documents)
