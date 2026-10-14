"""T099 (AC-EVL-07): the script writes the manifest and the blind sheet, then applies the labels."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from calibration_sheet import Source, main  # noqa: E402
from docdesk.evals.calib_sheet import ChunkView  # noqa: E402
from docdesk.evals.report_data import ResultRecord  # noqa: E402

SOURCE = "seed:openfda:abc"


def golden_item(item_id: str, kind: str = "single_fact") -> dict:
    item = {
        "id": item_id, "type": kind, "split": "dev", "question": f"Question {item_id}?",
        "answerable": kind != "unanswerable", "gold_route": "documents",
        "gold_facts": ["Keep them dry"] if kind != "unanswerable" else [],
        "gold_evidence": [{"source": SOURCE, "text": "Store in a dry place."}]
        if kind != "unanswerable" else [],
    }
    if kind == "unanswerable":
        item.update(no_evidence_reason="never stated", absent_terms=["half-life"],
                    absence_scope="corpus")
    return item


def record(item_id: str, kind: str, answer: str) -> ResultRecord:
    metrics = {"status": "ok", "type": kind, "outcome": "answered", "faithfulness": 0.5}
    return ResultRecord(item_id, metrics, None, {"answer": answer, "used_ids": ["a", "b"]})


@pytest.fixture
def project(tmp_path: Path) -> Path:
    items = [golden_item(f"gi-{i:03d}") for i in range(1, 7)] + [
        golden_item("gi-050", "unanswerable")]
    folder = tmp_path / "evals" / "golden"
    folder.mkdir(parents=True)
    (folder / "batch.yaml").write_text(yaml.safe_dump(items, sort_keys=False), encoding="utf-8")
    return tmp_path


def make_source() -> Source:
    b0 = [record(f"gi-{i:03d}", "single_fact", f"B0 answer {i}.") for i in range(1, 7)]
    cap4 = [record("gi-001", "single_fact", "B0 answer 1."),  # same text, a duplicate
            record("gi-002", "single_fact", "A new answer 2."),
            record("gi-050", "unanswerable", "An invented answer.")]

    def runs(run_ids: list[str]):
        data = {"run-b0": b0, "run-cap4": cap4}
        return [(run_id, data[run_id]) for run_id in run_ids]

    def chunks(chunk_ids: list[str]):
        return [ChunkView(f"Label {c}", f"Text of {c}.") for c in chunk_ids]

    return Source(runs, chunks)


def write(project: Path, *extra: str) -> int:
    argv = ["--run", "run-b0", "--run", "run-cap4", "--size", "5", *extra]
    return main(argv, project_root=project, source=make_source(), today=date(2026, 10, 14))


def fill(sheet: Path) -> None:
    out = []
    for line in sheet.read_text(encoding="utf-8").splitlines():
        if line.startswith("key ") and line.endswith(":"):
            line += " covered"
        elif line in ("unsupported claims:",):
            line += " none"
        elif line == "contradicted:":
            line += " no"
        out.append(line)
    sheet.write_text("\n".join(out) + "\n", encoding="utf-8")


def test_ac_evl_07_calib_30_writes_the_manifest_and_the_sheet(project: Path, capsys) -> None:
    assert write(project) == 0
    manifest = yaml.safe_load(
        (project / "evals" / "calibration" / "manifest.yaml").read_text(encoding="utf-8"))
    assert manifest["pool_size"] == 8 and manifest["sample_size"] == 5
    assert manifest["per_category"]["unanswerable"] == 1  # the answered unanswerable is in
    assert manifest["outputs"][0]["run_id"] in ("run-b0", "run-cap4")
    sheet = (project / "docs" / "calibration" / "sheet.md").read_text(encoding="utf-8")
    assert "Question gi-" in sheet and "[c1] Label a" in sheet and "faithfulness" not in sheet
    assert "pool 8" in capsys.readouterr().out


def test_ac_evl_07_calib_31_an_existing_sheet_is_never_overwritten_without_force(
    project: Path,
) -> None:
    assert write(project) == 0
    with pytest.raises(SystemExit, match="already exists"):
        write(project)
    assert write(project, "--force") == 0


def test_ac_evl_07_calib_32_apply_refuses_a_partial_sheet_then_writes_labels(
    project: Path,
) -> None:
    write(project)
    sheet = project / "docs" / "calibration" / "sheet.md"
    with pytest.raises(SystemExit, match="not complete"):
        main(["--apply", str(sheet)], project_root=project, source=make_source())
    assert not (project / "evals" / "calibration" / "labels.yaml").exists()
    fill(sheet)
    assert main(["--apply", str(sheet)], project_root=project, source=make_source(),
                today=date(2026, 10, 16)) == 0
    labels = yaml.safe_load(
        (project / "evals" / "calibration" / "labels.yaml").read_text(encoding="utf-8"))
    assert labels["labeled_by"] == "ali" and labels["labeled_on"] == "2026-10-16"
    assert len(labels["labels"]) == 5


def test_ac_evl_07_calib_33_original_labels_are_not_overwritten(project: Path) -> None:
    write(project)
    sheet = project / "docs" / "calibration" / "sheet.md"
    fill(sheet)
    main(["--apply", str(sheet)], project_root=project, source=make_source())
    with pytest.raises(SystemExit, match="already exists"):
        main(["--apply", str(sheet)], project_root=project, source=make_source())


def test_ac_evl_07_calib_34_draft_flag_writes_the_honest_provenance(project: Path) -> None:
    write(project)
    sheet = project / "docs" / "calibration" / "sheet.md"
    fill(sheet)
    assert main(["--apply", str(sheet), "--draft"], project_root=project,
                source=make_source(), today=date(2026, 10, 14)) == 0
    labels = yaml.safe_load(
        (project / "evals" / "calibration" / "labels.yaml").read_text(encoding="utf-8"))
    assert labels["labeled_by"] == "claude"
    assert labels["provenance"] == "drafted by claude on 2026-10-14, review by ali pending"
    assert labels["reviewed_by"] == "pending"
