"""The review script writes a sheet under docs/golden_review and applies decisions back."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from docdesk.evals.golden.probe import Probe, ProbeChunk  # noqa: E402
from docdesk.evals.golden.schema import GoldenItem  # noqa: E402
from golden_review import load_titles, main  # noqa: E402

SOURCE = "seed:openfda:abc"
ITEM = {
    "id": "gi-001",
    "type": "single_fact",
    "split": "dev",
    "question": "Where should I keep these tablets?",
    "answerable": True,
    "gold_route": "documents",
    "gold_facts": ["Keep them in a dry place"],
    "gold_evidence": [{"source": SOURCE, "text": "Store in a dry place."}],
}


def project(tmp_path: Path) -> Path:
    """A fake project root with one corpus manifest and one batch file."""
    corpus = tmp_path / "data" / "corpus" / "openfda"
    corpus.mkdir(parents=True)
    (corpus / "manifest.json").write_text(json.dumps({"abc": {"title": "Example label"}}))
    batch = tmp_path / "evals" / "golden" / "batch1.yaml"
    batch.parent.mkdir(parents=True)
    batch.write_text(yaml.safe_dump([ITEM], sort_keys=False), encoding="utf-8")
    return batch


def test_ac_evl_01_titles_come_from_the_manifests_under_the_seed_key(tmp_path: Path) -> None:
    project(tmp_path)
    assert load_titles(tmp_path / "data" / "corpus") == {SOURCE: "Example label"}


def test_ac_evl_01_the_script_writes_a_sheet_and_apply_verifies_the_ok_items(
    tmp_path: Path,
) -> None:
    batch = project(tmp_path)
    assert main([str(batch)], project_root=tmp_path) == 0
    sheet = tmp_path / "docs" / "golden_review" / "batch1.md"
    text = sheet.read_text(encoding="utf-8")
    assert "Example label" in text
    sheet.write_text(text.replace("Decision:\n", "Decision: OK\n", 1), encoding="utf-8")
    assert main(["--apply", str(sheet)], project_root=tmp_path) == 0
    saved = yaml.safe_load(batch.read_text(encoding="utf-8"))[0]
    assert saved["verified"] is True
    assert saved["verified_by"] == "ali"


def test_ac_evl_01_the_script_reads_only_the_batch_file_it_is_given(tmp_path: Path) -> None:
    batch = project(tmp_path)
    (batch.parent / "broken.yaml").write_text("- id: nope\n", encoding="utf-8")
    other = dict(ITEM, id="gi-002")
    (batch.parent / "batch2.yaml").write_text(yaml.safe_dump([other]), encoding="utf-8")
    assert main([str(batch)], project_root=tmp_path) == 0
    text = (tmp_path / "docs" / "golden_review" / "batch1.md").read_text(encoding="utf-8")
    assert "## gi-001" in text
    assert "gi-002" not in text
    sheet = tmp_path / "docs" / "golden_review" / "batch1.md"
    sheet.write_text(text.replace("Decision:\n", "Decision: OK\n", 1), encoding="utf-8")
    assert main(["--apply", str(sheet)], project_root=tmp_path) == 0


def test_ac_evl_01_the_script_can_write_a_sheet_for_chosen_items_under_another_name(
    tmp_path: Path,
) -> None:
    batch = project(tmp_path)
    second = dict(ITEM, id="gi-002")
    batch.write_text(yaml.safe_dump([ITEM, second], sort_keys=False), encoding="utf-8")
    args = [str(batch), "--only", "gi-002", "--name", "batch1_changed"]
    assert main(args, project_root=tmp_path) == 0
    text = (tmp_path / "docs" / "golden_review" / "batch1_changed.md").read_text(encoding="utf-8")
    assert "## gi-002" in text and "## gi-001" not in text
    assert "Batch file: evals/golden/batch1.yaml" in text


def test_ac_evl_01_an_unknown_item_id_in_only_is_an_error(tmp_path: Path) -> None:
    batch = project(tmp_path)
    with pytest.raises(SystemExit, match="gi-404"):
        main([str(batch), "--only", "gi-404"], project_root=tmp_path)


def test_ac_evl_01_the_probe_flag_adds_retrieval_results_for_items_without_an_answer(
    tmp_path: Path,
) -> None:
    batch = project(tmp_path)
    unanswerable = {
        "id": "gi-055",
        "type": "unanswerable",
        "split": "dev",
        "question": "What is the usual adult dose of warfarin?",
        "answerable": False,
        "gold_route": "documents",
        "no_evidence_reason": "No document is about warfarin.",
        "absent_terms": ["warfarin"],
        "absence_scope": "corpus",
    }
    batch.write_text(yaml.safe_dump([ITEM, unanswerable], sort_keys=False), encoding="utf-8")
    asked: list[str] = []

    def fake_probe(items: list[GoldenItem]) -> dict[str, Probe]:
        asked.extend(item.id for item in items)
        return {"gi-055": Probe([ProbeChunk("Aspirin", 0.4, "aspirin text")], [])}

    assert main([str(batch), "--probe"], project_root=tmp_path, probe=fake_probe) == 0
    text = (tmp_path / "docs" / "golden_review" / "batch1.md").read_text(encoding="utf-8")
    assert asked == ["gi-055"]
    assert "aspirin text" in text and "keyword top 3: no chunk matched" in text


def test_ac_evl_01_verify_marks_only_the_listed_items_and_leaves_the_rest(tmp_path: Path) -> None:
    batch = project(tmp_path)
    second = dict(ITEM, id="gi-002")
    batch.write_text(yaml.safe_dump([ITEM, second], sort_keys=False), encoding="utf-8")
    assert main([str(batch), "--verify", "gi-002", "--by", "ali"], project_root=tmp_path) == 0
    saved = {entry["id"]: entry for entry in yaml.safe_load(batch.read_text(encoding="utf-8"))}
    assert saved["gi-002"]["verified"] is True
    assert saved["gi-002"]["verified_by"] == "ali"
    assert not saved["gi-001"].get("verified")


def test_ac_evl_01_verify_with_an_unknown_id_is_an_error_and_changes_nothing(
    tmp_path: Path,
) -> None:
    batch = project(tmp_path)
    before = batch.read_text(encoding="utf-8")
    with pytest.raises(SystemExit, match="gi-404"):
        main([str(batch), "--verify", "gi-001,gi-404"], project_root=tmp_path)
    assert batch.read_text(encoding="utf-8") == before
