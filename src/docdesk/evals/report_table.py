"""One markdown table helper shared by the report writers. No dash characters."""

from __future__ import annotations


def table(headers: list[str], rows: list[list[str]]) -> list[str]:
    """A markdown table as lines."""
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    return lines + ["| " + " | ".join(row) + " |" for row in rows]
