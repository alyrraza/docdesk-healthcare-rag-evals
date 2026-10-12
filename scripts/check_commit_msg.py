"""Validate a commit message subject line (used by the commit-msg git hook).

Format:  type(scope): subject
Example: feat(auth): add password hashing module

Allowed types: feat, fix, docs, test, refactor, perf, chore, build, ci,
eval (changes to the eval harness or golden set), prompt (changes to a prompt).
The subject must be 72 characters or fewer. Merge, revert and fixup commits
are allowed through untouched.

Usage (git passes the path of the message file):
    python scripts/check_commit_msg.py .git/COMMIT_EDITMSG
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

TYPES = "feat|fix|docs|test|refactor|perf|chore|build|ci|eval|prompt"
SUBJECT_RE = re.compile(rf"^({TYPES})(\([a-z0-9_-]+\))?: \S.*$")
MAX_SUBJECT = 72
PASS_THROUGH = ("Merge ", "Revert ", "fixup!", "squash!")


def first_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip() and not line.startswith("#"):
            return line.rstrip()
    return ""


def check_subject(subject: str) -> str | None:
    """Return an error message, or None when the subject is acceptable."""
    if not subject:
        return "empty commit message"
    if subject.startswith(PASS_THROUGH):
        return None
    if len(subject) > MAX_SUBJECT:
        return f"subject is {len(subject)} characters, limit is {MAX_SUBJECT}"
    if not SUBJECT_RE.match(subject):
        return f"subject must look like 'type(scope): text' with type in {TYPES}"
    return None


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: check_commit_msg.py <message-file>")
        return 2
    subject = first_line(Path(argv[0]).read_text(encoding="utf-8", errors="replace"))
    error = check_subject(subject)
    if error:
        print(f"Commit rejected: {error}\n  got: {subject!r}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
