"""T099 (AC-EVL-07): the script builds the synthetic manifest from the natural one, by code only."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from calibration_synthetic import SynthSource, main, sheet_entries  # noqa: E402
from docdesk.evals.calib_labels import parse_sheet  # noqa: E402
from docdesk.evals.calib_sample import answer_hash  # noqa: E402
from docdesk.evals.calib_sheet import ChunkView  # noqa: E402
from docdesk.evals.calib_synth import Candidate  # noqa: E402
from docdesk.evals.report_data import ResultRecord  # noqa: E402

MULTI = [f"gi-{i:03d}" for i in range(1, 8)]
SINGLE = [f"gi-{i:03d}" for i in range(11, 19)]
DRUGS = ["betadrug", "gammadrug", "deltadrug", "epsilondrug", "zetadrug", "etadrug"]


def golden_item(item_id: str, kind: str) -> dict:
    evidence = [{"source": f"seed:openfda:{item_id}-{k}", "text": f"Quote {k}."}
                for k in range(2 if kind == "multi_chunk" else 1)]
    return {"id": item_id, "type": kind, "split": "dev", "question": f"Question {item_id}?",
            "answerable": True, "gold_route": "documents",
            "gold_facts": ["Fact one", "Fact two"] if kind == "multi_chunk" else ["Fact one"],
            "gold_evidence": evidence}


def answer_of(item_id: str) -> str:
    return (f"First part {item_id}. Second part {item_id}." if item_id in MULTI
            else f"Single answer {item_id}.")


def record(item_id: str) -> ResultRecord:
    kind = "multi_chunk" if item_id in MULTI else "single_fact"
    metrics = {"status": "ok", "type": kind, "outcome": "answered"}
    metrics |= {"faithfulness": 0.4217, "correctness": 0.4217, "passed": False}
    trace = {"answer": answer_of(item_id), "used_ids": ["ch-a"], "judge_model": "judge-x",
             "faithfulness_labels": [{"claim": "JUDGE-CLAIM-MARKER", "label": "unsupported"}]}
    return ResultRecord(item_id, metrics, "unfaithful", trace)


def natural_manifest() -> dict:
    items = MULTI + SINGLE
    outputs = [{"n": n, "run_id": "run-1", "item_id": i, "category":
                "multi_chunk" if i in MULTI else "single_fact",
                "answer_hash": answer_hash(answer_of(i)),
                "key_points": 2 if i in MULTI else 1} for n, i in enumerate(items, start=1)]
    return {"created_on": "2026-10-14", "seed": 1, "sample_size": len(outputs),
            "runs": ["run-1"], "outputs": outputs}


@pytest.fixture
def project(tmp_path: Path) -> Path:
    folder = tmp_path / "evals" / "golden"
    folder.mkdir(parents=True)
    golden = [golden_item(i, "multi_chunk") for i in MULTI] + [
        golden_item(i, "single_fact") for i in SINGLE]
    (folder / "batch.yaml").write_text(yaml.safe_dump(golden, sort_keys=False), encoding="utf-8")
    calibration = tmp_path / "evals" / "calibration"
    calibration.mkdir(parents=True)
    (calibration / "manifest.yaml").write_text(
        yaml.safe_dump(natural_manifest(), sort_keys=False), encoding="utf-8")
    return tmp_path


def make_source(records: list[ResultRecord] | None = None) -> SynthSource:
    rows = records if records is not None else [record(i) for i in MULTI + SINGLE]
    dose = "The usual adult dose is {n} mg twice daily and rises slowly."
    found = [Candidate(f"ch-{d}", f"seed:openfda:{d}", d, dose.format(n=k + 5))
             for k, d in enumerate(DRUGS)]
    return SynthSource(
        runs=lambda ids: [("run-1", rows)],
        chunks=lambda ids: [ChunkView("alphadrug drug label", "Text.") for _ in ids],
        candidates=lambda: found)


def build(project: Path, source: SynthSource | None = None) -> int:
    return main([], project_root=project, source=source or make_source(),
                today=date(2026, 10, 14))


def read_manifest(project: Path) -> dict:
    path = project / "evals" / "calibration" / "manifest_synthetic.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_ac_evl_07_calib_60_builds_the_synthetic_manifest_from_the_natural_one(
    project: Path, capsys
) -> None:
    assert build(project) == 0
    manifest = read_manifest(project)
    assert manifest["counts"] == {"insertion": 5, "omission": 5}
    assert len({o["parent_item_id"] for o in manifest["outputs"]}) == 10
    first = manifest["outputs"][0]
    assert first["parent_answer_hash"] == answer_hash(answer_of(first["parent_item_id"]))
    assert "5 insertion, 5 omission" in capsys.readouterr().out


def test_ac_evl_07_calib_61_an_existing_synthetic_manifest_is_never_overwritten(
    project: Path,
) -> None:
    assert build(project) == 0
    before = (project / "evals" / "calibration" / "manifest_synthetic.yaml").read_bytes()
    with pytest.raises(SystemExit, match="already exists"):
        build(project)
    assert (project / "evals" / "calibration" / "manifest_synthetic.yaml").read_bytes() == before


def test_ac_evl_07_calib_62_a_natural_output_that_changed_since_sampling_stops_the_build(
    project: Path,
) -> None:
    changed = [record(i) for i in MULTI[1:] + SINGLE]  # gi-001 is gone from the stored rows
    with pytest.raises(SystemExit, match="gi-001"):
        build(project, make_source(changed))
    assert not (project / "evals" / "calibration" / "manifest_synthetic.yaml").exists()


def test_ac_evl_07_calib_63_the_natural_manifest_is_not_touched(project: Path) -> None:
    path = project / "evals" / "calibration" / "manifest.yaml"
    before = path.read_bytes()
    build(project)
    assert path.read_bytes() == before


SHEET = Path("docs") / "calibration" / "sheet_synthetic.md"
TELLS = ("synthetic", "insertion", "omission", "perturb", "syn-", "parent", "source_document",
         "seed:openfda", "manifest", "run-1")


def sheet_text(project: Path) -> str:
    build(project)
    assert main(["--sheet"], project_root=project, source=make_source()) == 0
    return (project / SHEET).read_text(encoding="utf-8")


def test_ac_evl_07_calib_64_the_sheet_has_the_natural_format_in_manifest_order(
    project: Path,
) -> None:
    text = sheet_text(project)
    manifest = read_manifest(project)
    parsed = parse_sheet(text)
    assert [parsed[n].item_id for n in sorted(parsed)] == [
        o["parent_item_id"] for o in manifest["outputs"]]
    assert "## 1 of 10 | " in text and "### Your labels" in text
    assert all(f"> {o['answer']}" in text for o in manifest["outputs"])
    kinds = [o["perturbation"] for o in manifest["outputs"]]
    assert kinds != sorted(kinds)  # the seeded order mixes the two kinds


def test_ac_evl_07_calib_65_the_sheet_is_blind_to_judge_output_and_to_the_perturbation(
    project: Path, judge_leak_words
) -> None:
    text = sheet_text(project)
    lowered = text.lower()
    manifest = read_manifest(project)
    keys = [o["source_document"] for o in manifest["outputs"] if "source_document" in o]
    hashes = [o[f] for o in manifest["outputs"] for f in ("answer_hash", "parent_answer_hash")]
    for word in (*judge_leak_words, *TELLS, *keys, *hashes):
        assert word.lower() not in lowered, word


def test_ac_evl_07_calib_66_an_existing_synthetic_sheet_is_never_overwritten(
    project: Path,
) -> None:
    sheet_text(project)
    before = (project / SHEET).read_bytes()
    with pytest.raises(SystemExit, match="already exists"):
        main(["--sheet"], project_root=project, source=make_source())
    assert (project / SHEET).read_bytes() == before


def test_ac_evl_07_calib_67_the_sheet_needs_the_manifest_and_leaves_the_natural_sheet_alone(
    project: Path,
) -> None:
    natural = project / "docs" / "calibration" / "sheet.md"
    natural.parent.mkdir(parents=True)
    natural.write_text("Ali is filling this in.\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="build the manifest first"):
        main(["--sheet"], project_root=project, source=make_source())
    sheet_text(project)
    assert natural.read_text(encoding="utf-8") == "Ali is filling this in.\n"


def test_ac_evl_07_calib_68_a_parent_whose_answer_is_in_two_runs_is_found_in_its_own_run(
    project: Path,
) -> None:
    runs = {"run-a": [record("gi-001"), record("gi-002")], "run-b": [record("gi-001")]}
    source = SynthSource(
        runs=lambda ids: [(run, runs[run]) for run in ids],
        chunks=lambda ids: [ChunkView("alphadrug drug label", "Text.") for _ in ids],
        candidates=lambda: [])
    outputs = [
        {"n": n, "parent_item_id": item, "parent_run_id": run, "answer": f"Cut {item}.",
         "parent_answer_hash": answer_hash(answer_of(item)),
         "answer_hash": answer_hash(f"Cut {item}.")}
        for n, (item, run) in enumerate([("gi-001", "run-b"), ("gi-002", "run-a")], start=1)]
    entries = sheet_entries({"outputs": outputs}, source, project)
    assert [e.output.run_id for e in entries] == ["run-b", "run-a"]
