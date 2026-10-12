"""JSON log formatting with the request trace id taken from a context variable."""

from __future__ import annotations

import json
import logging
from contextvars import ContextVar, Token
from datetime import UTC, datetime

_trace_id: ContextVar[str] = ContextVar("trace_id", default="-")


def bind_trace_id(trace_id: str) -> Token[str]:
    """Attach the trace id to this request so every log line can carry it."""
    return _trace_id.set(trace_id)


def current_trace_id() -> str:
    """Read the trace id without passing it through every function signature."""
    return _trace_id.get()


class JsonFormatter(logging.Formatter):
    """One JSON object per line so logs can be searched by field."""

    def format(self, record: logging.LogRecord) -> str:
        """Render a record with its trace id, falling back to the context variable."""
        data = {
            "time": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": getattr(record, "trace_id", None) or current_trace_id(),
        }
        if record.exc_info:
            data["exception"] = self.formatException(record.exc_info)
        return json.dumps(data)


def configure_logging(level: int = logging.INFO) -> None:
    """Install the JSON formatter on the root logger once at startup."""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
