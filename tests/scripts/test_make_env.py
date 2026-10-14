"""AC-DEP-01: the demo .env gets random secrets, never the placeholders from .env.example."""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from docdesk.core.config import PLACEHOLDER_WORDS  # noqa: E402
from make_env import build_env, write_env  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = (ROOT / ".env.example").read_text(encoding="utf-8")


def counting_secrets() -> itertools.count[int]:
    """A predictable secret source so the test can tell which secret landed where."""
    return itertools.count(1)


def parse(text: str) -> dict[str, str]:
    """Read KEY=value lines, ignoring comments."""
    pairs = (line.split("=", 1) for line in text.splitlines() if "=" in line and line[0] != "#")
    return {key: value for key, value in pairs}


def test_ac_dep_01_every_secret_is_replaced_and_no_placeholder_word_is_left() -> None:
    counter = counting_secrets()
    env = parse(build_env(TEMPLATE, lambda: f"secret{next(counter):040d}"))
    for key in ("JWT_SECRET", "ADMIN_PASSWORD", "POSTGRES_PASSWORD", "READONLY_PASSWORD"):
        assert env[key].startswith("secret"), key
    for key in ("DATABASE_URL", "READONLY_DATABASE_URL"):
        assert not any(word in env[key].lower() for word in PLACEHOLDER_WORDS), key


def test_ac_dep_01_database_urls_use_the_generated_passwords() -> None:
    counter = counting_secrets()
    env = parse(build_env(TEMPLATE, lambda: f"s{next(counter)}x"))
    assert f":{env['POSTGRES_PASSWORD']}@" in env["DATABASE_URL"]
    assert f":{env['READONLY_PASSWORD']}@" in env["READONLY_DATABASE_URL"]


def test_ac_dep_01_provider_keys_stay_empty() -> None:
    env = parse(build_env(TEMPLATE, lambda: "a" * 40))
    assert env["GROQ_API_KEY"] == "" and env["OPENROUTER_API_KEY"] == ""


def test_ac_dep_01_an_existing_env_file_is_never_overwritten(tmp_path: Path) -> None:
    target = tmp_path / ".env"
    target.write_text("KEEP=me\n", encoding="utf-8")
    assert write_env(TEMPLATE, target) is False
    assert target.read_text(encoding="utf-8") == "KEEP=me\n"


def test_ac_dep_01_a_new_env_file_is_written_with_random_secrets(tmp_path: Path) -> None:
    target = tmp_path / ".env"
    assert write_env(TEMPLATE, target) is True
    other = tmp_path / "second"
    write_env(TEMPLATE, other)
    first, second = parse(target.read_text("utf-8")), parse(other.read_text("utf-8"))
    assert first["JWT_SECRET"] != second["JWT_SECRET"] and len(first["JWT_SECRET"]) >= 32
