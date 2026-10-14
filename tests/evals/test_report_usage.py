"""T098a (AC-EVL-04): tokens and cost per model, read back from the disk cache entries."""

from __future__ import annotations

import json
import logging
from decimal import Decimal
from pathlib import Path

import pytest

from docdesk.evals.report_usage import usage_from_cache


def entry(directory: Path, name: str, model: str, tokens_in: int, tokens_out: int,
          cost: str) -> None:
    data = {"text": "x", "tokens_in": tokens_in, "tokens_out": tokens_out, "latency_ms": 1.0,
            "finish_reason": "stop", "model": model, "cost_usd": cost}
    (directory / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")


def test_ac_evl_04_usage_01_entries_are_added_up_per_model(tmp_path: Path) -> None:
    entry(tmp_path, "a", "gen-model", 100, 20, "0.001")
    entry(tmp_path, "b", "gen-model", 50, 10, "0.0005")
    entry(tmp_path, "c", "judge-model", 30, 5, "0.002")
    usage = usage_from_cache(tmp_path)
    assert [u.model for u in usage] == ["gen-model", "judge-model"]
    gen = usage[0]
    assert (gen.calls, gen.tokens_in, gen.tokens_out) == (2, 150, 30)
    assert gen.cost_usd == Decimal("0.0015")


def test_ac_evl_04_usage_02_a_missing_folder_gives_no_rows(tmp_path: Path) -> None:
    assert usage_from_cache(tmp_path / "nothing") == []


def test_ac_evl_04_usage_03_a_damaged_entry_is_logged_and_left_out(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    entry(tmp_path, "a", "gen-model", 100, 20, "0.001")
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
    with caplog.at_level(logging.WARNING):
        usage = usage_from_cache(tmp_path)
    assert [u.calls for u in usage] == [1]
    assert "broken.json" in caplog.text
