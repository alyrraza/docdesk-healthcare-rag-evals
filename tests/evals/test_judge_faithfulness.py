"""T090: the faithfulness judge returns claim labels, and code computes the score."""

from __future__ import annotations

import json
from pathlib import Path

from docdesk.evals.judges.faithfulness import faithfulness_score, judge_faithfulness
from docdesk.evals.judges.parser import JudgeParser
from docdesk.evals.judges.schemas import ClaimLabel, FaithfulnessJudgement
from docdesk.prompts.loader import load_prompt
from fakes.llm import FakeLLMClient

ROOT = Path(__file__).resolve().parents[2]
PROMPT = load_prompt(ROOT / "prompts" / "judge_faithfulness" / "judge_faithfulness.v2.md")
JUDGE_MODEL = "judge-model-from-config"
GOLD_FACT = "SECRET-GOLD-FACT-TEXT"


def reply(*labels: str) -> str:
    claims = [{"claim": f"claim {i}", "label": label} for i, label in enumerate(labels)]
    return json.dumps({"claims": claims})


def run(client: FakeLLMClient, answer: str = "Take it with food.", answered: bool = True):
    parser = JudgeParser(FaithfulnessJudgement)
    result = judge_faithfulness(
        prompt=PROMPT,
        parser=parser,
        client=client,
        model=JUDGE_MODEL,
        question="How should it be taken?",
        answer=answer,
        evidence="[c1] Label\nTake with food.",
        answered=answered,
    )
    return result, parser


def test_ac_evl_07_faith_01_score_is_supported_over_total() -> None:
    verdicts = ["supported", "supported", "unsupported", "contradicted"]
    labels = [ClaimLabel(claim=str(i), label=v) for i, v in enumerate(verdicts)]
    assert faithfulness_score(labels) == 0.5


def test_ac_evl_07_faith_02_zero_claims_has_no_score_and_is_counted() -> None:
    result, parser = run(FakeLLMClient([reply()]))
    assert result.score is None
    assert result.status == "no_claims"
    assert parser.failures == []


def test_ac_evl_07_faith_03_labels_are_kept_per_claim() -> None:
    result, _ = run(FakeLLMClient([reply("supported", "contradicted")]))
    assert [c.label for c in result.labels] == ["supported", "contradicted"]
    assert result.score == 0.5
    assert result.status == "scored"


def test_ac_evl_07_faith_04_abstain_or_empty_answer_does_not_call_the_judge() -> None:
    client = FakeLLMClient([])
    skipped, _ = run(client, answered=False)
    empty, _ = run(client, answer="   ")
    assert skipped.status == empty.status == "skipped"
    assert skipped.score is None and client.requests == []


def test_ac_evl_07_faith_05_parse_failure_is_counted_and_not_scored_as_zero() -> None:
    result, parser = run(FakeLLMClient(["not json at all"]))
    assert result.status == "parse_failed"
    assert result.score is None
    assert len(parser.failures) == 1


def test_ac_evl_07_faith_06_unknown_label_is_a_parse_failure() -> None:
    result, parser = run(FakeLLMClient([reply("maybe")]))
    assert result.status == "parse_failed"
    assert len(parser.failures) == 1


def test_ac_evl_07_faith_07_judge_sees_only_its_inputs_and_uses_the_config_model() -> None:
    client = FakeLLMClient([reply("supported")])
    run(client)
    request = client.requests[0]
    assert request.model == JUDGE_MODEL
    for text in ("How should it be taken?", "Take it with food.", "Take with food."):
        assert text in request.user
    assert GOLD_FACT not in request.system + request.user


def test_ac_evl_07_faith_08_usage_is_reported() -> None:
    result, _ = run(FakeLLMClient([reply("supported")]))
    assert result.usage.calls == 1
    assert result.usage.tokens_in > 0 and result.usage.cache_hit is False


def test_ac_evl_07_faith_09_prompt_is_versioned_with_a_hash() -> None:
    assert (PROMPT.name, PROMPT.version) == ("judge_faithfulness", "2.0.0")
    assert PROMPT.schema == "FaithfulnessJudgement@2"
    assert len(PROMPT.content_hash) == 64
    assert set(PROMPT.untrusted) == {"evidence", "answer"}
