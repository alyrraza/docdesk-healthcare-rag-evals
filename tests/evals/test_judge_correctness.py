"""T091: the correctness judge labels each reference key point, and code computes the score."""

from __future__ import annotations

import json
from pathlib import Path

from docdesk.evals.judges.correctness import correctness_score, judge_correctness
from docdesk.evals.judges.parser import JudgeParser
from docdesk.evals.judges.schemas import CorrectnessJudgement, KeyPointLabel
from docdesk.prompts.loader import load_prompt
from fakes.llm import FakeLLMClient

ROOT = Path(__file__).resolve().parents[2]
PROMPT = load_prompt(ROOT / "prompts" / "judge_correctness" / "judge_correctness.v2.md")
JUDGE_MODEL = "judge-model-from-config"
POINTS = ["Take with food", "Do not exceed two tablets"]
GOLD_QUOTE = "SECRET-GOLD-QUOTE-TEXT"


def reply(*labels: str) -> str:
    items = [{"point": i + 1, "label": label} for i, label in enumerate(labels)]
    return json.dumps({"key_points": items})


def run(client: FakeLLMClient, points: list[str] | None = None, answer: str = "Take with food.",
        answered: bool = True):
    parser = JudgeParser(CorrectnessJudgement)
    result = judge_correctness(
        prompt=PROMPT,
        parser=parser,
        client=client,
        model=JUDGE_MODEL,
        question="How should it be taken?",
        answer=answer,
        key_points=POINTS if points is None else points,
        answered=answered,
    )
    return result, parser


def labels(*names: str) -> list[KeyPointLabel]:
    return [KeyPointLabel(point=i + 1, label=n) for i, n in enumerate(names)]


def test_ac_evl_07_correct_01_score_is_covered_over_total() -> None:
    assert correctness_score(labels("covered", "missing", "contradicted", "covered")) == 0.5


def test_ac_evl_07_correct_02_extra_supported_information_is_not_an_error() -> None:
    # The judge has no label for extra content, so a long answer scores like a short one.
    result, _ = run(FakeLLMClient([reply("covered", "covered")]), answer="Take with food. " * 30)
    assert result.score == 1.0


def test_ac_evl_07_correct_03_missing_and_contradicted_both_count_against() -> None:
    result, _ = run(FakeLLMClient([reply("missing", "contradicted")]))
    assert result.score == 0.0
    assert result.contradicted == 1
    assert [x.label for x in result.labels] == ["missing", "contradicted"]


def test_ac_evl_07_correct_04_no_key_points_means_no_call() -> None:
    client = FakeLLMClient([])
    result, _ = run(client, points=[])
    assert result.status == "skipped" and result.score is None
    assert client.requests == []


def test_ac_evl_07_correct_05_abstained_answer_is_decided_by_code() -> None:
    client = FakeLLMClient([])
    result, _ = run(client, answered=False)
    assert result.status == "decided_by_code"
    assert result.score == 0.0
    assert [x.label for x in result.labels] == ["missing", "missing"]
    assert client.requests == []


def test_ac_evl_07_correct_06_parse_failure_is_counted_and_not_zero() -> None:
    result, parser = run(FakeLLMClient(["{broken"]))
    assert result.status == "parse_failed" and result.score is None
    assert len(parser.failures) == 1


def test_ac_evl_07_correct_07_labels_that_do_not_match_the_key_points_are_a_failure() -> None:
    for bad in (reply("covered"), reply("covered", "covered", "covered")):
        result, parser = run(FakeLLMClient([bad]))
        assert result.status == "parse_failed" and result.score is None
        assert len(parser.failures) == 1
    skipped_numbers = json.dumps({"key_points": [{"point": 1, "label": "covered"},
                                                 {"point": 1, "label": "missing"}]})
    result, parser = run(FakeLLMClient([skipped_numbers]))
    assert result.status == "parse_failed"


def test_ac_evl_07_correct_08_judge_sees_question_answer_and_key_points_only() -> None:
    client = FakeLLMClient([reply("covered", "covered")])
    run(client)
    request = client.requests[0]
    assert request.model == JUDGE_MODEL
    for text in ("How should it be taken?", "Take with food.", *POINTS):
        assert text in request.user
    assert GOLD_QUOTE not in request.system + request.user


def test_ac_evl_07_correct_09_prompt_is_versioned_with_a_hash() -> None:
    assert (PROMPT.name, PROMPT.version) == ("judge_correctness", "2.0.0")
    assert PROMPT.schema == "CorrectnessJudgement@2"
    assert len(PROMPT.content_hash) == 64
    assert set(PROMPT.untrusted) == {"answer"}
    assert "extra" in PROMPT.system.lower()


def test_ac_evl_07_correct_10_parser_reject_counts_a_failure_without_a_new_attempt() -> None:
    parser = JudgeParser(CorrectnessJudgement)
    parser.parse(reply("covered"))
    parser.reject("wrong number of labels")
    assert parser.attempts == 1 and parser.failures == ["wrong number of labels"]
