"""Checks that must pass before a run writes anything: pinned corpus and pinned prompt."""

from __future__ import annotations

from docdesk.db.repositories.fingerprint import CorpusFingerprint, differences
from docdesk.evals.config import EvalConfig
from docdesk.prompts.loader import PromptFile


class FingerprintMismatch(RuntimeError):
    """The stored corpus was built differently from what the config assumes."""


def check_fingerprint(config: EvalConfig, stored: CorpusFingerprint | None) -> None:
    """Refuse a corpus that was built differently from the config, naming what differs."""
    if stored is None:
        raise FingerprintMismatch(
            "no corpus fingerprint is stored, so the corpus cannot be tied to this config. "
            "Load the corpus with scripts/load_corpus.py first."
        )
    wrong = differences(stored, config.corpus_fingerprint())
    if wrong:
        raise FingerprintMismatch(
            f"the stored corpus differs from {config.id} in: {', '.join(wrong)}. "
            "Re-ingest the corpus with the config's settings, or use a config that matches it."
        )


def check_run_allowed(
    config: EvalConfig, answer_prompt: PromptFile, stored: CorpusFingerprint | None
) -> None:
    """Refuse a run whose numbers would not describe the pinned config."""
    check_fingerprint(config, stored)
    config.check_prompt(answer_prompt)
