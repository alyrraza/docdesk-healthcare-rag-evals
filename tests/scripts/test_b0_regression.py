"""The B0 regression check reports every number that moved, and nothing when all are equal."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from b0_regression import differences  # noqa: E402


def test_ac_evl_06_b0_regression_01_equal_summaries_have_no_differences() -> None:
    summary = {"categories": {"all": {"mrr": {"mean": 0.8, "n": 30}}}}
    assert differences(summary, {"categories": {"all": {"mrr": {"mean": 0.8, "n": 30}}}}) == []


def test_ac_evl_06_b0_regression_02_a_moved_number_is_named_with_its_path() -> None:
    old = {"categories": {"all": {"mrr": {"mean": 0.8, "n": 30}}}}
    new = {"categories": {"all": {"mrr": {"mean": 0.81, "n": 30}}}}
    assert differences(old, new) == ["/categories/all/mrr/mean: committed 0.8, now 0.81"]


def test_ac_evl_06_b0_regression_03_a_missing_key_counts_as_a_difference() -> None:
    assert differences({"a": 1}, {"b": 1}) == [
        "/a: present in only one summary", "/b: present in only one summary"]
