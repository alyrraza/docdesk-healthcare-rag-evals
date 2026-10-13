"""Token counting must follow the model's own tokenizer and ignore its truncation (AC-ING-05)."""

from __future__ import annotations

from pathlib import Path

import pytest
from tokenizers import Tokenizer, models, pre_tokenizers

from docdesk.embeddings.tokenizer import TokenCounter

WORDS = ["[UNK]", "the", "patient", "takes", "aspirin", "daily"]


def build_tokenizer(truncate_at: int | None = None) -> Tokenizer:
    """A tiny word-level tokenizer, so the tests need no downloaded model."""
    vocab = {word: index for index, word in enumerate(WORDS)}
    tokenizer = Tokenizer(models.WordLevel(vocab, unk_token="[UNK]"))
    tokenizer.pre_tokenizer = pre_tokenizers.Whitespace()
    if truncate_at is not None:
        tokenizer.enable_truncation(max_length=truncate_at)
    return tokenizer


def test_ac_ing_05_count_returns_the_number_of_tokens() -> None:
    counter = TokenCounter(build_tokenizer())
    assert counter.count("the patient takes aspirin daily") == 5


def test_ac_ing_05_empty_text_has_zero_tokens() -> None:
    assert TokenCounter(build_tokenizer()).count("") == 0


def test_ac_ing_05_unknown_words_still_count_as_tokens() -> None:
    assert TokenCounter(build_tokenizer()).count("the patient takes warfarin") == 4


def test_ac_ing_05_count_ignores_the_tokenizers_own_truncation() -> None:
    """A model file may truncate at 128 tokens; a budget check must still see the full length."""
    counter = TokenCounter(build_tokenizer(truncate_at=2))
    assert counter.count("the patient takes aspirin daily") == 5


def test_ac_ing_05_from_file_loads_a_saved_tokenizer(tmp_path: Path) -> None:
    path = tmp_path / "tokenizer.json"
    build_tokenizer().save(str(path))
    assert TokenCounter.from_file(path).count("the patient") == 2


def test_ac_ing_05_from_file_reports_a_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="tokenizer.json"):
        TokenCounter.from_file(tmp_path / "tokenizer.json")
