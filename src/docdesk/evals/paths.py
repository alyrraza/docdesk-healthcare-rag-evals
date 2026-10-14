"""Project root anchored paths, so a run started from any folder uses the same files."""

from __future__ import annotations

from pathlib import Path

# src/docdesk/evals/paths.py -> the project root is three folders up.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
LEDGER_PATH = PROJECT_ROOT / ".cache" / "ledger.json"
LLM_CACHE_DIR = PROJECT_ROOT / ".cache" / "llm"
GOLDEN_DIR = PROJECT_ROOT / "evals" / "golden"
PROMPTS_DIR = PROJECT_ROOT / "prompts"
DEFAULT_CONFIG = PROJECT_ROOT / "evals" / "configs" / "b0.toml"
