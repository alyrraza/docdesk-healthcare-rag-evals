"""Fail when a markdown file contains an em dash or an en dash.

Why this exists: the owner's writing rule bans both characters in every
document (README, notes, prompts, LinkedIn drafts). A rule that only lives in
a document gets forgotten, so this script enforces it.

The characters are written as escapes below so this file itself stays clean.

Usage:
    python scripts/check_docs_style.py             # scan every .md file
    python scripts/check_docs_style.py a.md b.md   # scan only these files
"""

from __future__ import annotations

import sys
from pathlib import Path

BANNED = {"—": "em dash", "–": "en dash"}
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", ".hf-cache"}


def scan_file(path: Path) -> list[tuple[int, str]]:
    """Return (line_number, character_name) for every banned character."""
    hits = []
    text = path.read_text(encoding="utf-8", errors="replace")
    for number, line in enumerate(text.splitlines(), start=1):
        for char, name in BANNED.items():
            if char in line:
                hits.append((number, name))
    return hits


def collect(argv: list[str]) -> list[Path]:
    if argv:
        return [Path(a) for a in argv if a.endswith(".md")]
    return [
        p for p in Path(".").rglob("*.md")
        if not any(part in SKIP_DIRS for part in p.parts)
    ]


def main(argv: list[str]) -> int:
    failed = False
    for path in collect(argv):
        if not path.is_file():
            continue
        for number, name in scan_file(path):
            print(f"{path}:{number}: contains an {name}. Rewrite the sentence.")
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
