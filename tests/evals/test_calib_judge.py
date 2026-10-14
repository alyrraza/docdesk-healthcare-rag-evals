"""T100 (AC-EVL-07): the synthetic outputs go through the same two judges as a real run."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from docdesk.context.packer import format_item
from docdesk.evals.calib_judge import JudgeRunError, context_text, judge_synthetic
from docdesk.evals.calib_sample import answer_hash
from docdesk.evals.calib_sheet import ChunkView
from docdesk.evals.judges.kit import load_judge_kit
from fakes.llm import FakeLLMClient

ANSWER = "Tablets are 25 mg. In addition, the dose is 900 mg."
FAITH = json.dumps({"claims": [{"claim": "25 mg", "label": "supported", "evidence_id": "c1"},
                               {"claim": "900 mg", "label": "unsupported"}]})
CORRECT = json.dumps({"key_points": [{"point": 2, "label": "missing"},
                                     {"point": 1, "label": "covered"}]})
MANIFEST = {"outputs": [{"n": 1, "synthetic_id": "syn-01", "parent_item_id": "gi-001",
                         "answer": ANSWER, "answer_hash": answer_hash(ANSWER)}]}
QUESTIONS = {"gi-001": "What strengths exist?"}
FACTS = {"gi-001": ["Tablets come in 25 mg", "Take with food"]}
CONTEXTS = {"syn-01": "[c1] Label\nTablets 25 mg."}


def run(client: FakeLLMClient):
    kit = load_judge_kit(Path("prompts"), client, "judge-model-from-config")
    return judge_synthetic(MANIFEST, QUESTIONS, FACTS, CONTEXTS, kit)


def test_ac_evl_07_judge_01_context_is_built_the_way_the_runner_builds_it() -> None:
    views = [ChunkView("Label A", "Text A."), ChunkView("Label B", "Text B.")]
    chunks = [SimpleNamespace(document_title=v.title, text=v.text) for v in views]
    expected = "\n\n".join(format_item(f"c{n}", c) for n, c in enumerate(chunks, start=1))
    assert context_text(views) == expected


def test_ac_evl_07_judge_02_each_output_gets_both_judges_on_its_exact_text() -> None:
    client = FakeLLMClient([FAITH, CORRECT])
    document = run(client)
    faith_request, correct_request = client.requests
    assert ANSWER in faith_request.system + faith_request.user
    assert CONTEXTS["syn-01"] in faith_request.system + faith_request.user
    assert "1. Tablets come in 25 mg" in correct_request.system + correct_request.user
    assert {r.model for r in client.requests} == {"judge-model-from-config"}
    (result,) = document["results"]
    assert result["synthetic_id"] == "syn-01" and result["answer_hash"] == answer_hash(ANSWER)
    assert result["faithfulness"]["status"] == "scored" and result["faithfulness"]["score"] == 0.5
    assert result["faithfulness"]["claims"][1]["label"] == "unsupported"
    assert result["correctness"]["key_points"][0] == {"point": 1, "label": "covered"}
    assert document["judge_model"] == "judge-model-from-config" and document["prompts"]
    assert result["usage"]["tokens_in"] > 0


def test_ac_evl_07_judge_03_a_reply_that_does_not_parse_stops_the_run() -> None:
    with pytest.raises(JudgeRunError, match="syn-01.*faithfulness.*parse_failed"):
        run(FakeLLMClient(["not json"]))
    with pytest.raises(JudgeRunError, match="syn-01.*correctness.*parse_failed"):
        run(FakeLLMClient([FAITH, "not json"]))


def test_ac_evl_07_judge_04_a_provider_error_is_not_swallowed() -> None:
    with pytest.raises(ConnectionError):
        run(FakeLLMClient([ConnectionError("down")]))
