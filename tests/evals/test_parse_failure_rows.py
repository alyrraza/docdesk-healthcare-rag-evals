"""F21: the run summary counts judge parse failures from stored rows, not from this process."""

from __future__ import annotations

from docdesk.evals.run_store import parse_failed_items


def test_ac_evl_08_rows_01_failures_come_from_rows_so_a_resume_still_shows_them() -> None:
    rows = {
        "gi-001": {"faithfulness_status": "parse_failed", "correctness_status": "scored"},
        "gi-002": {"faithfulness_status": "scored", "correctness_status": "parse_failed"},
        "gi-003": {"faithfulness_status": "scored", "correctness_status": "scored"},
        "gi-004": {"status": "not_run"},
    }
    found = parse_failed_items(rows)
    assert found == {"faithfulness": ["gi-001"], "correctness": ["gi-002"]}
