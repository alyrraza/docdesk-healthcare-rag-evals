"""T101 (AC-EVL-06): the small CI corpus and its golden subset stay valid, small and honest."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from docdesk.evals.golden.evidence import check_quote, cleaned_document_text
from docdesk.evals.golden.schema import GoldenItem

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "evals" / "ci" / "corpus"
SUBSET = ROOT / "evals" / "ci" / "golden" / "ci_subset.yaml"
REAL_GOLDEN = ROOT / "evals" / "golden"
MAX_DOCUMENTS = 20
MAX_TOTAL_BYTES = 60_000


def subset_items() -> list[dict]:
    """The raw subset entries, so tests can compare them with the real golden files."""
    return yaml.safe_load(SUBSET.read_text(encoding="utf-8"))


def real_items() -> dict[str, dict]:
    """Every real golden item by id."""
    found: dict[str, dict] = {}
    for path in sorted(REAL_GOLDEN.glob("*.yaml")):
        for entry in yaml.safe_load(path.read_text(encoding="utf-8")):
            found[entry["id"]] = entry
    return found


def manifest() -> dict[str, dict[str, str]]:
    """The fixture manifest in the same format the seed loader reads."""
    return json.loads((CORPUS / "medlineplus" / "manifest.json").read_text(encoding="utf-8"))


def test_ac_evl_06_subset_items_are_valid_golden_items() -> None:
    for entry in subset_items():
        GoldenItem.model_validate(entry)


def test_ac_evl_06_subset_is_dev_only_verified_and_answerable() -> None:
    items = subset_items()
    assert len(items) >= 10
    for entry in items:
        assert entry["split"] == "dev", entry["id"]
        assert entry["verified"] is True, entry["id"]
        assert entry["answerable"] is True, entry["id"]
        assert entry["gold_route"] == "documents", entry["id"]
        assert entry["type"] in {"single_fact", "multi_chunk"}, entry["id"]


def test_ac_evl_06_subset_items_are_verbatim_copies_of_real_golden_items() -> None:
    real = real_items()
    for entry in subset_items():
        assert entry == real[entry["id"]], f"{entry['id']} drifted from evals/golden"


def test_ac_evl_06_every_quote_is_in_a_fixture_document() -> None:
    files = manifest()
    for entry in subset_items():
        for evidence in entry["gold_evidence"]:
            prefix, source_id = evidence["source"].rsplit(":", 1)
            assert prefix == "seed:medlineplus", evidence["source"]
            data = (CORPUS / "medlineplus" / files[source_id]["file"]).read_bytes()
            check_quote(cleaned_document_text(data), evidence["text"])


def test_ac_evl_06_fixture_corpus_stays_small() -> None:
    files = manifest()
    assert 2 <= len(files) <= MAX_DOCUMENTS
    total = sum((CORPUS / "medlineplus" / item["file"]).stat().st_size for item in files.values())
    assert total <= MAX_TOTAL_BYTES


def test_ac_evl_06_fixture_has_distractor_documents() -> None:
    cited = {
        evidence["source"].rsplit(":", 1)[1]
        for entry in subset_items()
        for evidence in entry["gold_evidence"]
    }
    assert set(manifest()) - cited, "every document is cited, so nothing can be confused"
