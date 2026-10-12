"""Tests for core/ids.py and core/clock.py."""

from __future__ import annotations

import re
from datetime import UTC, datetime

import pytest

from docdesk.core import clock
from docdesk.core.ids import new_trace_id


def test_trace_id_is_32_hex_characters() -> None:
    assert re.fullmatch(r"[0-9a-f]{32}", new_trace_id())


def test_trace_ids_are_unique() -> None:
    assert len({new_trace_id() for _ in range(1000)}) == 1000


def test_utc_now_is_timezone_aware_utc() -> None:
    assert clock.utc_now().tzinfo == UTC


def test_clock_can_be_frozen_in_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    frozen = datetime(2026, 1, 1, tzinfo=UTC)
    monkeypatch.setattr(clock, "utc_now", lambda: frozen)
    assert clock.utc_now() == frozen
