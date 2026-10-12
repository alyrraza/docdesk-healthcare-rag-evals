"""Fail when a source file is longer than its limit.

Why this exists: the project rule is "one responsibility per file". Line count
is a crude proxy, but it is the cheapest one a script can enforce, and it stops
the 1200 line file before it exists.

Usage:
    python scripts/check_file_length.py            # scan the whole repo
    python scripts/check_file_length.py a.py b.ts  # scan only these files
                                                   # (the pre-commit hook does this)
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC_LIMIT = 200
TEST_LIMIT = 300
CHECKED_SUFFIXES = {".py", ".ts", ".tsx"}
SKIP_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".hf-cache",
    "versions",  # alembic migration files are generated
    "dist", "build",
}


def limit_for(path: Path) -> int | None:
    """Return the line limit for this file, or None if it is not checked."""
    if path.suffix not in CHECKED_SUFFIXES:
        return None
    if any(part in SKIP_DIRS for part in path.parts):
        return None
    return TEST_LIMIT if "tests" in path.parts else SRC_LIMIT


def count_lines(path: Path) -> int:
    return len(path.read_text(encoding="utf-8", errors="replace").splitlines())


def find_offenders(paths: list[Path]) -> list[tuple[Path, int, int]]:
    """Return (path, line_count, limit) for every file over its limit."""
    offenders = []
    for path in paths:
        limit = limit_for(path)
        if limit is None or not path.is_file():
            continue
        lines = count_lines(path)
        if lines > limit:
            offenders.append((path, lines, limit))
    return offenders


def main(argv: list[str]) -> int:
    paths = [Path(a) for a in argv] if argv else list(Path(".").rglob("*"))
    offenders = find_offenders(paths)
    for path, lines, limit in offenders:
        print(f"{path}: {lines} lines, limit is {limit}. Split it by responsibility.")
    return 1 if offenders else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
