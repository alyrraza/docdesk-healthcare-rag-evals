"""T100 (AC-EVL-07): the summary and the report are built by code from the joined outputs."""

from __future__ import annotations

import json

from docdesk.evals.calib_join import JudgedOutput, JudgeSide
from docdesk.evals.calib_report import render_markdown
from docdesk.evals.calibration import Provenance, build_summary

DRAFT = "drafted by claude on 2026-10-14, review by ali pending"
PENDING = Provenance("claude", "2026-10-14", DRAFT, "pending")
REVIEWED = Provenance("claude", "2026-10-14", "drafted by claude on 2026-10-14", "ali")


def out(set_name: str, n: int, ref_keys, judge_keys, *, score=1.0, ref_claims=(),
        borderline=False) -> JudgedOutput:
    side = JudgeSide("scored", score, [("a claim", "supported" if score == 1.0 else "unsupported")],
                     list(judge_keys))
    name = str(n) if set_name == "natural" else f"syn-{n:02d}"
    texts = [f"fact {k}" for k in range(1, len(ref_keys) + 1)]
    return JudgedOutput(set_name, n, name, "gi-001", borderline, texts, list(ref_keys),
                        list(ref_claims), False, side)


def natural() -> list[JudgedOutput]:
    rows = [out("natural", n, ["covered"], ["covered"]) for n in range(1, 9)]
    rows.append(out("natural", 9, ["covered"], ["missing"], score=0.5, borderline=True))
    rows.append(out("natural", 10, ["covered"], ["covered"], ref_claims=["bad"], score=0.5))
    return rows


def synthetic() -> list[JudgedOutput]:
    return [out("synthetic", 1, ["covered"], ["covered"], ref_claims=["bad"], score=0.5),
            out("synthetic", 2, ["covered"], ["covered"], ref_claims=["bad"], score=1.0,
                borderline=True),
            out("synthetic", 3, ["missing"], ["missing"]),
            out("synthetic", 4, ["covered"], ["covered"])]


def summary(provenance: Provenance = PENDING) -> dict:
    meta = {"model": "judge-x", "prompts": {"judge_faithfulness@2.0.0": "abc"}}
    return build_summary(natural(), synthetic(), provenance, provenance, meta,
                         resamples=200, seed=0)


def test_ac_evl_07_report_01_sets_are_separate_and_each_has_all_and_without_borderline() -> None:
    result = summary()
    assert list(result["sets"]) == ["natural", "synthetic"]
    variants = result["sets"]["natural"]["variants"]
    assert variants["all"]["n_outputs"] == 10 and variants["without_borderline"]["n_outputs"] == 9
    assert result["sets"]["synthetic"]["variants"]["without_borderline"]["n_outputs"] == 3
    assert result["bootstrap"] == {"resamples": 200, "seed": 0, "confidence": 0.95}


def test_ac_evl_07_report_02_the_summary_is_plain_json_and_repeatable() -> None:
    assert json.dumps(summary(), sort_keys=True) == json.dumps(summary(), sort_keys=True)
    measure = summary()["sets"]["natural"]["variants"]["all"]["measures"]["correct_item"]
    assert measure["n"] == 10 and measure["table"] == [[0, 0], [1, 9]]
    assert measure["agreement"] == 0.9 and measure["kappa"] is None


def test_ac_evl_07_report_03_provenance_sentence_follows_the_review_state() -> None:
    assert "drafted by Claude" in summary()["provenance"]
    assert "not been reviewed" in summary()["provenance"]
    assert "measure the judge against Claude drafted labels" in summary()["provenance"]
    assert "not been reviewed" not in summary(REVIEWED)["provenance"]


def test_ac_evl_07_report_04_the_top_of_the_report_states_the_caveats_and_no_verdict() -> None:
    text = render_markdown(summary())
    top = text.split("## ")[0]
    assert summary()["provenance"] in top
    assert "small" in top and "almost all faithful" in top and "built by code" in top
    assert "200 resamples" in top and "seed 0" in top
    assert "no pass or fail verdict" in top.lower()


def test_ac_evl_07_report_05_no_dash_characters_and_no_pooled_section() -> None:
    text = render_markdown(summary())
    assert "—" not in text and "–" not in text
    assert text.count("## Natural outputs") == 1 and text.count("## Synthetic outputs") == 1


def test_ac_evl_07_report_06_a_single_class_shows_counts_instead_of_a_kappa() -> None:
    natural_part = render_markdown(summary()).split("## Synthetic outputs")[0]
    assert "| Correctness, item level | 10 | 0.900 | undefined, single class |" in natural_part


def test_ac_evl_07_report_07_each_disagreement_has_its_facts_and_borderline_flag() -> None:
    text = render_markdown(summary())
    natural_part, synthetic_part = text.split("### Disagreements")[1:]
    assert "| 9 | key point | covered | missing | key 1: fact 1 | yes |" in natural_part
    assert "| syn-02 | faithfulness item | not faithful | faithful |" in synthetic_part
    assert synthetic_part.rstrip().endswith("| yes |")  # syn-02 is the borderline one


def test_ac_evl_07_report_08_the_detection_counts_are_listed() -> None:
    detection = summary()["sets"]["synthetic"]["variants"]["all"]["detection"]
    assert (detection["tp"], detection["fn"]) == (1, 1) and detection["recall"] == 0.5
    assert "recall" in render_markdown(summary()).lower()


def test_ac_evl_07_report_09_dashes_inside_label_text_are_shown_as_hyphens() -> None:
    risky = out("natural", 11, ["covered"], ["missing"])
    risky = JudgedOutput(**{**risky.__dict__, "key_points": ["dose \u2014 twice \u2013 daily"]})
    meta = {"model": "judge-x", "prompts": {}}
    text = render_markdown(build_summary([risky], synthetic(), PENDING, PENDING, meta,
                                         resamples=50, seed=0))
    assert "dose - twice - daily" in text
    assert "\u2014" not in text and "\u2013" not in text
