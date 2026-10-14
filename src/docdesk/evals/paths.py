"""Project root anchored paths, so a run started from any folder uses the same files."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

# src/docdesk/evals/paths.py -> the project root is three folders up.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
LEDGER_PATH = PROJECT_ROOT / ".cache" / "ledger.json"
POOL_LEDGER_PATH = PROJECT_ROOT / ".cache" / "pool_ledger.json"


def resolve_cache_dir(env: Mapping[str, str]) -> Path:
    """Why: a smoke run of the key pool needs a cold cache without touching the real one."""
    override = env.get("DOCDESK_LLM_CACHE_DIR")
    return Path(override) if override else PROJECT_ROOT / ".cache" / "llm"


LLM_CACHE_DIR = resolve_cache_dir(os.environ)
GOLDEN_DIR = PROJECT_ROOT / "evals" / "golden"
PROMPTS_DIR = PROJECT_ROOT / "prompts"
DEFAULT_CONFIG = PROJECT_ROOT / "evals" / "configs" / "b0.toml"
