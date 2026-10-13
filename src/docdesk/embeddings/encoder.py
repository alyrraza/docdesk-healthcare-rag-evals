"""ONNX sentence encoder: tokenize, run in batches, mean-pool and normalize like the model card."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

PAD_TOKEN = "[PAD]"


class Encoder:
    """Turns texts into unit length vectors so cosine similarity is a plain dot product."""

    def __init__(
        self,
        session: Any,
        tokenizer: Tokenizer,
        *,
        model_name: str,
        revision: str,
        batch_size: int = 32,
        max_length: int = 256,
    ) -> None:
        """Take the session as an argument so tests can pass a fake instead of a model file."""
        pad_id = tokenizer.token_to_id(PAD_TOKEN)
        if pad_id is None:
            raise ValueError(f"tokenizer has no {PAD_TOKEN} token, cannot pad batches")
        tokenizer.enable_padding(pad_id=pad_id, pad_token=PAD_TOKEN)
        tokenizer.enable_truncation(max_length=max_length)
        self._session = session
        self._tokenizer = tokenizer
        self._input_names = [model_input.name for model_input in session.get_inputs()]
        self._batch_size = batch_size
        self.model_name = model_name
        self.revision = revision

    @classmethod
    def from_directory(cls, directory: Path, batch_size: int = 32) -> Encoder:
        """Load a model folder (onnx/model.onnx, tokenizer.json, REVISION) from the local cache."""
        session = ort.InferenceSession(
            str(directory / "onnx" / "model.onnx"), providers=["CPUExecutionProvider"]
        )
        return cls(
            session,
            Tokenizer.from_file(str(directory / "tokenizer.json")),
            model_name=directory.name,
            revision=(directory / "REVISION").read_text(encoding="utf-8").strip(),
            batch_size=batch_size,
        )

    def encode(self, texts: list[str]) -> np.ndarray:
        """Return one normalized vector per text, in the same order as the input."""
        batches = [
            self._encode_batch(texts[start : start + self._batch_size])
            for start in range(0, len(texts), self._batch_size)
        ]
        return np.concatenate(batches) if batches else np.zeros((0, 0), dtype=np.float32)

    def _encode_batch(self, texts: list[str]) -> np.ndarray:
        """Run one padded batch through the model and pool it to one vector per text."""
        encodings = self._tokenizer.encode_batch(texts)
        arrays = {
            "input_ids": np.array([e.ids for e in encodings], dtype=np.int64),
            "attention_mask": np.array([e.attention_mask for e in encodings], dtype=np.int64),
            "token_type_ids": np.array([e.type_ids for e in encodings], dtype=np.int64),
        }
        feeds = {name: arrays[name] for name in self._input_names}
        hidden = self._session.run(None, feeds)[0]
        return normalize(mean_pool(hidden, arrays["attention_mask"]))


def mean_pool(hidden: np.ndarray, attention_mask: np.ndarray) -> np.ndarray:
    """Average token vectors, counting only real tokens so padding cannot dilute the meaning."""
    mask = attention_mask[:, :, None].astype(np.float32)
    return (hidden * mask).sum(axis=1) / np.maximum(mask.sum(axis=1), 1e-9)


def normalize(vectors: np.ndarray) -> np.ndarray:
    """Scale each row to length one, leaving an all-zero row as zeros instead of dividing by 0."""
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return (vectors / np.maximum(norms, 1e-12)).astype(np.float32)
