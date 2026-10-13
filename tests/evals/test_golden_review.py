"""The review sheet: drafts out as markdown, the owner's decisions back in (AC-EVL-01)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import yaml

from docdesk.evals.golden.review import (
    SheetError,
    apply_decisions,
    parse_sheet,
    render_sheet,
)
from docdesk.evals.golden.schema import GoldenItem

SOURCE = "seed:openfda:abc"
TITLE = "Example Tablets drug label"


def draft(item_id: str, **changes: object) -> dict[str, object]:
    """A valid unverified single fact item as a YAML-ready dict."""
    item: dict[str, object] = {
        "id": item_id,
        "type": "single_fact",
        "split": "dev",
        "question": "Where should I keep these tablets?",
        "answerable": True,
        "gold_route": "documents",
        "gold_facts": ["Keep them in a dry place"],
        "gold_evidence": [{"source": SOURCE, "text": "Store in a dry place."}],
    }
    return {**item, **changes}


def write_batch(path: Path, *items: dict[str, object]) -> Path:
    path.write_text(yaml.safe_dump(list(items), sort_keys=False), encoding="utf-8")
    return path


def test_ac_evl_01_the_sheet_shows_everything_the_owner_must_check() -> None:
    item = GoldenItem.model_validate(draft("gi-001", split="test"))
    sheet = render_sheet([item], {SOURCE: TITLE}, "evals/golden/batch1.yaml")
    for expected in (
        "## gi-001",
        "single_fact",
        "test",
        "Where should I keep these tablets?",
        "Keep them in a dry place",
        SOURCE,
        TITLE,
        "Store in a dry place.",
        "Decision:",
    ):
        assert expected in sheet


def test_ac_evl_01_a_source_with_no_known_title_is_shown_as_unknown() -> None:
    item = GoldenItem.model_validate(draft("gi-001"))
    assert "title unknown" in render_sheet([item], {}, "b.yaml")


def test_ac_evl_01_the_sheet_remembers_which_batch_file_it_came_from() -> None:
    item = GoldenItem.model_validate(draft("gi-001"))
    sheet = render_sheet([item], {SOURCE: TITLE}, "evals/golden/batch1.yaml")
    assert parse_sheet(sheet).batch_file == "evals/golden/batch1.yaml"


def test_ac_evl_01_decisions_are_read_as_ok_fix_with_a_note_or_drop() -> None:
    sheet = (
        "Batch file: b.yaml\n\n"
        "## gi-001\nDecision: OK\n\n"
        "## gi-002\nDecision: FIX: the quote is from the wrong section\n\n"
        "## gi-003\nDecision: drop\n\n"
        "## gi-004\nDecision:\n"
    )
    decisions = parse_sheet(sheet).decisions
    assert decisions["gi-001"].kind == "OK"
    assert (decisions["gi-002"].kind, decisions["gi-002"].note) == (
        "FIX",
        "the quote is from the wrong section",
    )
    assert decisions["gi-003"].kind == "DROP"
    assert decisions["gi-004"].kind == "UNDECIDED"


def test_ac_evl_01_a_decision_word_that_is_not_understood_is_an_error() -> None:
    with pytest.raises(SheetError, match="gi-001.*maybe"):
        parse_sheet("Batch file: b.yaml\n\n## gi-001\nDecision: maybe\n")


def test_ac_evl_01_a_sheet_without_a_batch_file_line_is_an_error() -> None:
    with pytest.raises(SheetError, match="Batch file"):
        parse_sheet("## gi-001\nDecision: OK\n")


def test_ac_evl_01_apply_sets_verified_true_only_for_ok_items(tmp_path: Path) -> None:
    batch = write_batch(tmp_path / "b.yaml", draft("gi-001"), draft("gi-002"), draft("gi-003"))
    sheet = (
        f"Batch file: {batch}\n\n## gi-001\nDecision: OK\n\n"
        "## gi-002\nDecision: FIX: shorten\n\n## gi-003\nDecision: DROP\n"
    )
    result = apply_decisions(parse_sheet(sheet), by="ali", today=date(2026, 10, 20))
    saved = {entry["id"]: entry for entry in yaml.safe_load(batch.read_text(encoding="utf-8"))}
    assert saved["gi-001"]["verified"] is True
    assert saved["gi-001"]["verified_by"] == "ali"
    assert saved["gi-001"]["verified_on"] == date(2026, 10, 20)
    assert not saved["gi-002"].get("verified")
    assert not saved["gi-003"].get("verified")
    assert result.verified == ["gi-001"]
    assert result.fix == [("gi-002", "shorten")]
    assert result.dropped == ["gi-003"]


def test_ac_evl_01_apply_leaves_undecided_items_untouched(tmp_path: Path) -> None:
    batch = write_batch(tmp_path / "b.yaml", draft("gi-001"))
    sheet = f"Batch file: {batch}\n\n## gi-001\nDecision:\n"
    result = apply_decisions(parse_sheet(sheet), by="ali", today=date(2026, 10, 20))
    assert result.undecided == ["gi-001"]
    assert "verified" not in yaml.safe_load(batch.read_text(encoding="utf-8"))[0]


def test_ac_evl_01_an_ok_item_that_is_not_in_the_batch_file_is_an_error(tmp_path: Path) -> None:
    batch = write_batch(tmp_path / "b.yaml", draft("gi-001"))
    sheet = f"Batch file: {batch}\n\n## gi-009\nDecision: OK\n"
    with pytest.raises(SheetError, match="gi-009"):
        apply_decisions(parse_sheet(sheet), by="ali", today=date(2026, 10, 20))
    assert "verified" not in yaml.safe_load(batch.read_text(encoding="utf-8"))[0]


def test_ac_evl_01_a_batch_item_marked_ok_loads_as_a_valid_verified_item(tmp_path: Path) -> None:
    batch = write_batch(tmp_path / "b.yaml", draft("gi-001"))
    sheet = f"Batch file: {batch}\n\n## gi-001\nDecision: OK\n"
    apply_decisions(parse_sheet(sheet), by="ali", today=date(2026, 10, 20))
    item = GoldenItem.model_validate(yaml.safe_load(batch.read_text(encoding="utf-8"))[0])
    assert item.verified is True
