"""Tests for core/logging.py: JSON log lines that carry the trace id."""

from __future__ import annotations

import json
import logging

from docdesk.core.logging import JsonFormatter, bind_trace_id, current_trace_id


def make_record(message: str) -> logging.LogRecord:
    return logging.LogRecord("docdesk.test", logging.INFO, __file__, 1, message, None, None)


def test_log_line_is_json_with_core_fields() -> None:
    line = JsonFormatter().format(make_record("hello"))
    data = json.loads(line)
    assert data["message"] == "hello"
    assert data["level"] == "INFO"
    assert data["logger"] == "docdesk.test"
    assert "time" in data


def test_log_line_carries_the_bound_trace_id() -> None:
    token = bind_trace_id("trace-123")
    try:
        data = json.loads(JsonFormatter().format(make_record("x")))
    finally:
        token.var.reset(token)
    assert data["trace_id"] == "trace-123"


def test_trace_id_defaults_to_dash_when_unbound() -> None:
    assert current_trace_id() == "-"


def test_exception_text_is_included() -> None:
    try:
        raise ValueError("bad")
    except ValueError:
        import sys

        record = logging.LogRecord(
            "docdesk.test", logging.ERROR, __file__, 1, "failed", None, sys.exc_info()
        )
    data = json.loads(JsonFormatter().format(record))
    assert "ValueError: bad" in data["exception"]
