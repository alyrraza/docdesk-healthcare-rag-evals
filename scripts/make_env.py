"""Write a .env with random secrets from .env.example, for the Docker demo and local runs.

Usage (project root, needs only the Python standard library):
    python scripts/make_env.py
An existing .env is never overwritten. Provider keys stay empty: add your own GROQ_API_KEY by hand.
"""

from __future__ import annotations

import secrets
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRET_KEYS = ("JWT_SECRET", "ADMIN_PASSWORD", "POSTGRES_PASSWORD", "READONLY_PASSWORD")
# The database urls carry one of the generated passwords in place of the placeholder.
URL_PASSWORD = {"DATABASE_URL": "POSTGRES_PASSWORD", "READONLY_DATABASE_URL": "READONLY_PASSWORD"}


def build_env(template: str, make_secret: Callable[[], str]) -> str:
    """Why: a copied .env.example is refused at startup, so the demo needs real random secrets."""
    values = {key: make_secret() for key in SECRET_KEYS}
    lines = []
    for line in template.splitlines():
        key, sep, rest = line.partition("=")
        if sep and key in values:
            line = f"{key}={values[key]}"
        elif sep and key in URL_PASSWORD:
            line = f"{key}={rest.replace('change-me', values[URL_PASSWORD[key]])}"
        lines.append(line)
    return "\n".join(lines) + "\n"


def write_env(template: str, target: Path) -> bool:
    """Why: running the command twice must not throw away a key the user already pasted in."""
    if target.exists():
        return False
    target.write_text(build_env(template, lambda: secrets.token_hex(24)), encoding="utf-8")
    return True


if __name__ == "__main__":
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    created = write_env(example, ROOT / ".env")
    print("wrote .env with random secrets" if created else ".env already exists, left as it is")
    sys.exit(0)
