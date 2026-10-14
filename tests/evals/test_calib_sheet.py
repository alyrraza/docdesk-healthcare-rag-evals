"""T099 (AC-EVL-07): the calibration sheet is blind, quick to fill, and strict when applied."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import yaml

from docdesk.evals.calib_labels import LabelError, apply_sheet, parse_sheet
from docdesk.evals.calib_sample import SEED, pool_from_runs, sample_outputs
from docdesk.evals.calib_sheet import ChunkView, SheetEntry, manifest_of, render_sheet
from docdesk.evals.report_data import ResultRecord

TODAY = date(2026, 10, 15)


def judged_record(item_id: str, category: str, answer: str) -> ResultRecord:
    """A stored row carrying every judge field a leak could come from."""
    metrics = {"status": "ok", "type": category, "outcome": "answered", "faithfulness": 0.4217,
               "correctness": 0.4217, "passed": False, "faithfulness_status": "scored",
               "correctness_status": "decided_by_code", "contradicted": 1}
    trace = {"answer": answer, "used_ids": ["ch-1", "ch-2"], "judge_model": "judge-x",
             "judge_prompts": {"faithfulness": "abc"},
             "faithfulness_labels": [{"claim": "JUDGE-CLAIM-MARKER", "label": "unsupported"}],
             "correctness_labels": [{"point": 1, "label": "missing"}]}
    return ResultRecord(item_id, metrics, "unfaithful", trace)


def entries_for(outputs, key_points: dict[str, list[str]]) -> list[SheetEntry]:
    return [SheetEntry(n, o, f"Question for {o.item_id}?",
                       [ChunkView("Label A", f"Text one of {o.item_id}."),
                        ChunkView("Label B", "Text two.")],
                       key_points.get(o.item_id, ["Fact one", "Fact two"]))
            for n, o in enumerate(outputs, start=1)]


@pytest.fixture
def entries() -> list[SheetEntry]:
    rows = [judged_record(f"gi-{i:03d}", "single_fact", f"Answer {i} with food.")
            for i in range(1, 6)]
    rows.append(judged_record("gi-090", "unanswerable", "A made up answer."))
    sample = sample_outputs(pool_from_runs([("run-a", rows)]), size=4, seed=SEED)
    return entries_for(sample.outputs, {"gi-090": []})


def manifest(entries: list[SheetEntry]) -> dict:
    return manifest_of(entries, seed=SEED, pool_size=6, shortfall=0, created=date(2026, 10, 14))


def test_ac_evl_07_calib_10_the_sheet_shows_the_task_and_no_judge_output(
    entries, judge_leak_words
) -> None:
    text = render_sheet(entries)
    assert "Question for" in text and "[c1] Label A" in text and "[c2] Label B" in text
    assert "1. Fact one" in text and "2. Fact two" in text
    assert "key 1:" in text and "unsupported claims:" in text and "contradicted:" in text
    lowered = text.lower()
    for word in judge_leak_words:
        assert word.lower() not in lowered, word


def test_ac_evl_07_calib_11_an_item_without_key_points_has_only_the_claim_fields(entries) -> None:
    text = render_sheet(entries)
    section = next(s for s in text.split("\n## ")[1:] if "gi-090" in s.splitlines()[0])
    assert "key 1:" not in section and "unsupported claims:" in section
    assert "no key points" in section


def test_ac_evl_07_calib_12_dashes_in_source_text_are_replaced_for_the_style_check() -> None:
    chunk = ChunkView("T", "Dose — range 5–10 mg.")
    rows = [judged_record("gi-1", "single_fact", "A")]
    sample = sample_outputs(pool_from_runs([("r", rows)]), size=1, seed=SEED)
    text = render_sheet([SheetEntry(1, sample.outputs[0], "Q?", [chunk], ["k"])])
    assert "—" not in text and "–" not in text and "Dose - range 5-10 mg." in text


def test_ac_evl_07_calib_13_the_manifest_names_every_output_by_run_item_and_hash(entries) -> None:
    result = manifest(entries)
    first = result["outputs"][0]
    assert set(first) == {"n", "run_id", "item_id", "category", "answer_hash", "key_points"}
    assert result["seed"] == SEED and result["pool_size"] == 6
    assert sum(result["per_category"].values()) == 4


def fill(text: str, **overrides: str) -> str:
    """Fill every field of the sheet with a valid value, then apply per field overrides."""
    out = []
    for line in text.splitlines():
        head = line[:-1] if line.endswith(":") else ""
        if head.startswith("key "):
            line += " " + overrides.get(head.replace(" ", "_"), "covered")
        elif line == "unsupported claims:":
            line += " " + overrides.get("claims", "none")
        elif line == "contradicted:":
            line += " " + overrides.get("contradicted", "no")
        out.append(line)
    return "\n".join(out) + "\n"


def test_ac_evl_07_calib_14_a_complete_sheet_is_applied_with_who_and_when(entries) -> None:
    filled = fill(render_sheet(entries), claims="the dose is 5 mg")
    labels = apply_sheet(parse_sheet(filled), manifest(entries), by="ali", today=TODAY)
    assert labels["labeled_by"] == "ali" and labels["labeled_on"] == "2026-10-15"
    first = labels["labels"][0]
    assert first["answer_hash"] == manifest(entries)["outputs"][0]["answer_hash"]
    assert first["unsupported_claims"] == ["the dose is 5 mg"] and first["contradicted"] is False
    assert len(labels["labels"]) == 4


def test_ac_evl_07_calib_15_none_means_no_unsupported_claims(entries) -> None:
    filled = fill(render_sheet(entries))
    labels = apply_sheet(parse_sheet(filled), manifest(entries), by="ali", today=TODAY)
    assert labels["labels"][0]["unsupported_claims"] == []
    expected = ["covered"] * manifest(entries)["outputs"][0]["key_points"]
    assert labels["labels"][0]["key_points"] == expected


def test_ac_evl_07_calib_16_claims_may_be_bullets_under_the_field(entries) -> None:
    text = fill(render_sheet(entries)).replace(
        "unsupported claims: none", "unsupported claims:\n- first claim\n- second claim", 1)
    labels = apply_sheet(parse_sheet(text), manifest(entries), by="ali", today=TODAY)
    assert labels["labels"][0]["unsupported_claims"] == ["first claim", "second claim"]


def test_ac_evl_07_calib_17_a_partial_sheet_is_refused_and_lists_everything_missing(
    entries,
) -> None:
    with pytest.raises(LabelError) as error:
        apply_sheet(parse_sheet(render_sheet(entries)), manifest(entries), by="ali", today=TODAY)
    message = str(error.value)
    assert "output 1" in message and "key 1" in message and "unsupported claims" in message
    assert "contradicted" in message and "output 4" in message


def test_ac_evl_07_calib_18_only_allowed_values_are_accepted(entries) -> None:
    bad = fill(render_sheet(entries), contradicted="maybe", key_1="partly")
    with pytest.raises(LabelError) as error:
        apply_sheet(parse_sheet(bad), manifest(entries), by="ali", today=TODAY)
    assert "'partly'" in str(error.value) and "'maybe'" in str(error.value)


def test_ac_evl_07_calib_19_a_sheet_that_lost_an_output_is_refused(entries) -> None:
    text = fill(render_sheet(entries))
    cut = text[: text.index("## 4 of 4")]
    with pytest.raises(LabelError, match="output 4"):
        apply_sheet(parse_sheet(cut), manifest(entries), by="ali", today=TODAY)


def test_ac_evl_07_calib_20_labels_yaml_round_trips(entries, tmp_path: Path) -> None:
    labels = apply_sheet(parse_sheet(fill(render_sheet(entries))), manifest(entries),
                         by="ali", today=TODAY)
    path = tmp_path / "labels.yaml"
    path.write_text(yaml.safe_dump(labels, sort_keys=False), encoding="utf-8")
    assert yaml.safe_load(path.read_text(encoding="utf-8")) == labels
