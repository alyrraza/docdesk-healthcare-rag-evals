"""Prove that the B0 config still gives the committed B0 dev retrieval numbers, exactly.

Usage (project root, OPENBLAS_NUM_THREADS=1; needs the dev database and the embedding model):
    python scripts/b0_regression.py
Run it after every code change to retrieval, packing, scoring or the config loader. It makes no
model call and reads only the dev split. Exit 1 lists every number that moved.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from b0_rows import collect_rows
from b0_summary import summarize
from docdesk.api.query_deps import build_encoder
from docdesk.core.config import get_settings
from docdesk.db.session import default_session_factory
from docdesk.evals.cli_runtime import corpus_for
from docdesk.evals.config import load_eval_config
from docdesk.evals.paths import DEFAULT_CONFIG, GOLDEN_DIR, PROJECT_ROOT

COMMITTED = PROJECT_ROOT / "evals" / "results" / "b0_retrieval_dev_summary.json"


def differences(expected: Any, actual: Any, path: str = "") -> list[str]:
    """Why: the check must say which number moved, so it walks both summaries together."""
    if isinstance(expected, dict) and isinstance(actual, dict):
        found: list[str] = []
        for key in sorted(set(expected) | set(actual)):
            if key not in expected or key not in actual:
                found.append(f"{path}/{key}: present in only one summary")
            else:
                found += differences(expected[key], actual[key], f"{path}/{key}")
        return found
    return [] if expected == actual else [f"{path}: committed {expected!r}, now {actual!r}"]


def main() -> int:
    """Rebuild the B0 dev summary and compare it with the committed one."""
    config = load_eval_config(DEFAULT_CONFIG)
    encoder = build_encoder(get_settings().model_dir)
    with default_session_factory()() as session:
        rows = collect_rows(session, corpus_for(session), encoder, config, GOLDEN_DIR)
    now = json.loads(json.dumps(summarize(rows, config.retrieval_config().top_k)))
    committed = json.loads(COMMITTED.read_text(encoding="utf-8"))
    moved = differences(committed, now)
    for line in moved:
        print(f"MOVED {line}")
    print(f"B0 regression: {'FAILED, ' + str(len(moved)) + ' numbers moved' if moved else 'ok'}")
    return 1 if moved else 0


if __name__ == "__main__":
    sys.exit(main())
