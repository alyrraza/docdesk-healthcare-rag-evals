"""The example env file must list every setting, so a new clone knows what to fill in."""

from __future__ import annotations

from pathlib import Path

from docdesk.core.config import Settings

ROOT = Path(__file__).resolve().parents[2]


def test_env_example_lists_every_setting() -> None:
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    listed = {line.split("=", 1)[0] for line in text.splitlines() if "=" in line}
    expected = {name.upper() for name in Settings.model_fields}
    assert expected <= listed


def test_env_example_holds_no_real_secret() -> None:
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "change-me" in text
