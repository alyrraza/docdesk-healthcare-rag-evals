"""The bundle id changes whenever anything that shapes the output changes (AC-PRM-03)."""

from __future__ import annotations

from dataclasses import replace

from docdesk.prompts.bundle import BundleParts, bundle_id

BASE = BundleParts(
    prompt_name="answer",
    prompt_version="1.0.0",
    prompt_hash="a" * 64,
    model="openai/gpt-oss-120b",
    params={"temperature": 0, "max_output_tokens": 600},
    schema_version="AnswerOutput@1",
    retrieval_config_id="hybrid-n20-k5-rrf60",
)


def test_ac_prm_03_the_same_parts_always_give_the_same_id() -> None:
    assert bundle_id(BASE) == bundle_id(replace(BASE))
    assert len(bundle_id(BASE)) == 16


def test_ac_prm_03_the_order_of_the_params_does_not_matter() -> None:
    swapped = replace(BASE, params={"max_output_tokens": 600, "temperature": 0})
    assert bundle_id(BASE) == bundle_id(swapped)


def test_ac_prm_03_changing_any_single_part_gives_a_new_id() -> None:
    changes = {
        "prompt_version": "1.0.1",
        "prompt_hash": "b" * 64,
        "model": "qwen/qwen3.8-27b",
        "params": {"temperature": 0.2, "max_output_tokens": 600},
        "schema_version": "AnswerOutput@2",
        "retrieval_config_id": "dense-n20-k5-rrf60",
    }
    ids = {bundle_id(replace(BASE, **{field: value})) for field, value in changes.items()}
    assert len(ids | {bundle_id(BASE)}) == len(changes) + 1


def test_ac_prm_03_a_model_switch_with_unchanged_prompt_text_is_a_new_bundle() -> None:
    assert bundle_id(replace(BASE, model="other/model")) != bundle_id(BASE)
