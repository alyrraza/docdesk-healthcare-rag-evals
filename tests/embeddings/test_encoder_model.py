"""The real MiniLM ONNX file behaves like the fake: right shape, unit length, sensible meaning."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from docdesk.embeddings.encoder import Encoder

pytestmark = pytest.mark.model

MODEL_DIR = Path(__file__).resolve().parents[2] / ".cache" / "models" / "all-MiniLM-L6-v2"


@pytest.fixture(scope="module")
def encoder() -> Encoder:
    """Load the downloaded model once, and fail loudly if it was not downloaded."""
    if not (MODEL_DIR / "onnx" / "model.onnx").is_file():
        pytest.fail(f"model files missing under {MODEL_DIR}; see docs/REMEMBER.md")
    return Encoder.from_directory(MODEL_DIR, batch_size=4)


def test_ac_ing_05_real_model_gives_384_numbers_of_unit_length(encoder: Encoder) -> None:
    vectors = encoder.encode(["aspirin lowers fever", "metformin treats diabetes"])
    assert vectors.shape == (2, 384)
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-5)


def test_ac_ing_05_real_model_puts_related_sentences_closer(encoder: Encoder) -> None:
    query, related, unrelated = encoder.encode(
        ["medicine for lowering blood sugar", "metformin treats type 2 diabetes", "the cat sat"]
    )
    assert float(query @ related) > float(query @ unrelated)


def test_ac_ing_05_real_model_gives_the_same_vector_alone_or_in_a_batch(encoder: Encoder) -> None:
    text = "ibuprofen can irritate the stomach"
    alone = encoder.encode([text])[0]
    batched = encoder.encode(["a much longer sentence about something else entirely " * 3, text])[1]
    assert np.allclose(alone, batched, atol=1e-4)


def test_ac_ing_05_real_model_name_and_revision_come_from_the_folder(encoder: Encoder) -> None:
    assert encoder.model_name == "all-MiniLM-L6-v2"
    assert len(encoder.revision) == 40
