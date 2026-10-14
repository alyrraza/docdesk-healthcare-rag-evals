"""The batch check script resolves one file against a corpus and reports each problem by item id."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals"))

from test_golden_duplicates import DuplicateCorpus, write  # noqa: E402

from golden_check import check_batch  # noqa: E402


def test_ac_evl_01_check_batch_reports_a_duplicate_quote_by_item_id(tmp_path: Path) -> None:
    write(tmp_path, "Where should the tablets be kept away from?")
    good, problems = check_batch(tmp_path / "a.yaml", DuplicateCorpus())
    assert good == []
    assert len(problems) == 1 and problems[0].startswith("gi-001: quote is also in")


def test_ac_evl_01_check_batch_passes_an_item_that_names_its_document(tmp_path: Path) -> None:
    write(tmp_path, "Who must the alphamab tablets be kept away from?")
    good, problems = check_batch(tmp_path / "a.yaml", DuplicateCorpus())
    assert problems == [] and len(good) == 1
