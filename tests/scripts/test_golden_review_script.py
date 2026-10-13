"""The review script writes a sheet under docs/golden_review and applies decisions back."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

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
