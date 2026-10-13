"""Token counting with the embedding model's own tokenizer, shared by chunker and packer."""

from __future__ import annotations

from pathlib import Path

from tokenizers import Tokenizer


class TokenCounter:
    """Counts tokens so chunk sizes and context budgets are measured the way the model sees text."""

    def __init__(self, tokenizer: Tokenizer) -> None:
        """Keep the tokenizer with truncation and padding off, so counts are never capped."""
        tokenizer.no_truncation()
        tokenizer.no_padding()
        self._tokenizer = tokenizer

    @classmethod
    def from_file(cls, path: Path) -> TokenCounter:
        """Load the tokenizer.json that ships with the model, failing clearly if it is absent."""
        if not path.is_file():
            raise FileNotFoundError(f"tokenizer.json not found at {path}")
        return cls(Tokenizer.from_file(str(path)))

    def count(self, text: str) -> int:
        """Return how many tokens the text uses, without the special start and end tokens."""
        return len(self._tokenizer.encode(text, add_special_tokens=False).ids)
