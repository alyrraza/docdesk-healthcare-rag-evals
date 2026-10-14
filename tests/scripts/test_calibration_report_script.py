"""T100 (AC-EVL-07): the script writes the report and summary from stored files, by code only."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from calibration_report import JSON_OUT, MARKDOWN_OUT, main  # noqa: E402
from calibration_sheet import Source  # noqa: E402
from docdesk.evals.calib_sample import answer_hash  # noqa: E402
from docdesk.evals.report_data import ResultRecord  # noqa: E402

ANSWER = "The tablets are 25 mg."
SYNTHETIC = "Tablets are 25 mg. In addition, the dose is 900 mg."
DRAFT = {"labeled_by": "claude", "labeled_on": "2026-10-14", "reviewed_by": "pending",
         "provenance": "drafted by claude on 2026-10-14, review by ali pending"}


def write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


@pytest.fixture
def project(tmp_path: Path) -> Path:
    golden = [{"id": "gi-001", "type": "single_fact", "split": "dev", "question": "Strengths?",
               "answerable": True, "gold_route": "documents",
               "gold_facts": ["Tablets come in 25 mg", "Take with food"],
               "gold_evidence": [{"source": "seed:openfda:a", "text": "25 mg"}]}]
    write(tmp_path / "evals" / "golden" / "batch.yaml", golden)
    cal = tmp_path / "evals" / "calibration"
    entry = {"n": 1, "run_id": "run-1", "item_id": "gi-001", "key_points": 2,
             "answer_hash": answer_hash(ANSWER)}
    write(cal / "manifest.yaml", {"runs": ["run-1"], "outputs": [entry]})
    write(cal / "labels.yaml", {**DRAFT, "labels": [{
        **entry, "key_points": ["covered", "missing"], "unsupported_claims": [],
        "contradicted": False}]})
    syn = {"n": 1, "synthetic_id": "syn-01", "parent_item_id": "gi-001", "parent_run_id": "run-1",
           "answer": SYNTHETIC, "answer_hash": answer_hash(SYNTHETIC), "key_points": 2}
    write(cal / "manifest_synthetic.yaml", {"outputs": [syn]})
    write(cal / "labels_synthetic.yaml", {**DRAFT, "labels": [{
        "synthetic_id": "syn-01", "n": 1, "run_id": "run-1", "item_id": "gi-001",
        "answer_hash": answer_hash(SYNTHETIC), "key_points": ["covered", "missing"],
        "unsupported_claims": ["the dose is 900 mg"], "contradicted": False}]})
    write(cal / "judge_results_synthetic.yaml", {
        "judge_model": "judge-x", "prompts": {"judge_faithfulness@2.0.0": "abcdef123456789"},
        "results": [{
            "synthetic_id": "syn-01", "n": 1, "parent_item_id": "gi-001",
            "answer_hash": answer_hash(SYNTHETIC),
            "faithfulness": {"status": "scored", "score": 0.5, "claims": [
                {"claim": "dose — 900 mg", "label": "unsupported", "evidence_id": None}]},
            "correctness": {"status": "scored", "score": 0.5, "key_points": [
                {"point": 1, "label": "covered"}, {"point": 2, "label": "missing"}]}}]})
    return tmp_path


def source(answer: str = ANSWER) -> Source:
    metrics = {"faithfulness": 1.0, "faithfulness_status": "scored", "correctness": 0.5,
               "correctness_status": "scored"}
    trace = {"answer": answer, "judge_model": "judge-x",
             "judge_prompts": {"judge_faithfulness@2.0.0": "abcdef123456789"},
             "faithfulness_labels": [{"claim": "25 mg", "label": "supported"}],
             "correctness_labels": [{"point": 1, "label": "covered"},
                                    {"point": 2, "label": "missing"}]}
    rows = [ResultRecord("gi-001", metrics, None, trace)]
    return Source(runs=lambda ids: [(i, rows) for i in ids], chunks=lambda ids: [])


def test_ac_evl_07_reportscript_01_writes_the_markdown_and_the_json(project: Path) -> None:
    assert main([], project_root=project, source=source(), resamples=50) == 0
    text = (project / MARKDOWN_OUT).read_text(encoding="utf-8")
    assert text.startswith("# Judge calibration report")
    assert "have not been reviewed by Ali" in text.split("## ")[0]
    summary = json.loads((project / JSON_OUT).read_text(encoding="utf-8"))
    assert list(summary["sets"]) == ["natural", "synthetic"]
    assert summary["judge"]["model"] == "judge-x"
    assert summary["bootstrap"]["resamples"] == 50


def test_ac_evl_07_reportscript_02_the_output_is_repeatable_and_free_of_dashes(
    project: Path,
) -> None:
    main([], project_root=project, source=source(), resamples=50)
    first = [(project / name).read_bytes() for name in (MARKDOWN_OUT, JSON_OUT)]
    main([], project_root=project, source=source(), resamples=50)
    assert first == [(project / name).read_bytes() for name in (MARKDOWN_OUT, JSON_OUT)]
    for blob in first:
        assert "—".encode() not in blob and "–".encode() not in blob
        assert b"\\u2014" not in blob and b"\\u2013" not in blob


def test_ac_evl_07_reportscript_03_a_changed_stored_answer_stops_with_the_join_error(
    project: Path,
) -> None:
    with pytest.raises(SystemExit, match="hash"):
        main([], project_root=project, source=source("A different answer."), resamples=50)
    assert not (project / MARKDOWN_OUT).exists()
