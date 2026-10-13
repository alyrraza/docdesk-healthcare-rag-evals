"""The encoder turns text into unit vectors in order, with padding ignored (AC-ING-05)."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest
from tokenizers import Tokenizer, models, pre_tokenizers

from docdesk.embeddings.encoder import Encoder

VOCAB = {"[PAD]": 0, "the": 1, "patient": 2, "takes": 3, "aspirin": 4, "daily": 5, "[UNK]": 6}


class FakeSession:
    """Stands in for onnxruntime: each token's hidden state is [token id, 1, 0, 0]."""

    def __init__(self) -> None:
        self.batch_sizes: list[int] = []

    def get_inputs(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(name="input_ids"), SimpleNamespace(name="attention_mask")]

    def run(self, _outputs: None, feeds: dict[str, np.ndarray]) -> list[np.ndarray]:
        ids = feeds["input_ids"]
        self.batch_sizes.append(ids.shape[0])
        hidden = np.zeros((*ids.shape, 4), dtype=np.float32)
        hidden[:, :, 0] = ids
        hidden[:, :, 1] = 1.0
        return [hidden]


def build_encoder(batch_size: int = 32, max_length: int = 16) -> tuple[Encoder, FakeSession]:
    tokenizer = Tokenizer(models.WordLevel(VOCAB, unk_token="[UNK]"))
    tokenizer.pre_tokenizer = pre_tokenizers.Whitespace()
    session = FakeSession()
    encoder = Encoder(
        session, tokenizer, model_name="fake", revision="r1", batch_size=batch_size,
        max_length=max_length,
    )  # fmt: skip
    return encoder, session


def unit(*values: float) -> np.ndarray:
    vector = np.array(values, dtype=np.float32)
    return vector / np.linalg.norm(vector)


def test_ac_ing_05_output_has_one_row_per_text_and_the_model_width() -> None:
    encoder, _ = build_encoder()
    assert encoder.encode(["the patient", "aspirin"]).shape == (2, 4)


def test_ac_ing_05_every_vector_has_length_one() -> None:
    encoder, _ = build_encoder()
    norms = np.linalg.norm(encoder.encode(["the patient", "takes aspirin daily"]), axis=1)
    assert np.allclose(norms, 1.0, atol=1e-6)


def test_ac_ing_05_padding_tokens_are_left_out_of_the_average() -> None:
    """'the patient' (ids 1, 2) padded next to a longer text must still average to [1.5, 1]."""
    encoder, _ = build_encoder()
    vectors = encoder.encode(["the patient", "the patient takes aspirin daily"])
    assert np.allclose(vectors[0], unit(1.5, 1, 0, 0), atol=1e-6)
    assert np.allclose(vectors[1], unit(3.0, 1, 0, 0), atol=1e-6)


def test_ac_ing_05_batches_are_split_and_the_order_is_kept() -> None:
    encoder, session = build_encoder(batch_size=2)
    texts = ["the", "patient", "takes", "aspirin", "daily"]
    vectors = encoder.encode(texts)
    assert session.batch_sizes == [2, 2, 1]
    for row, expected_id in zip(vectors, [1, 2, 3, 4, 5], strict=True):
        assert np.allclose(row, unit(expected_id, 1, 0, 0), atol=1e-6)


def test_ac_ing_05_no_texts_gives_an_empty_matrix_without_calling_the_model() -> None:
    encoder, session = build_encoder()
    assert encoder.encode([]).shape[0] == 0
    assert session.batch_sizes == []


def test_ac_ing_05_text_longer_than_max_length_is_cut_not_rejected() -> None:
    encoder, _ = build_encoder(max_length=2)
    vector = encoder.encode(["the patient takes aspirin daily"])[0]
    assert np.allclose(vector, unit(1.5, 1, 0, 0), atol=1e-6)


def test_ac_ing_05_the_model_name_and_revision_are_exposed_for_chunk_rows() -> None:
    encoder, _ = build_encoder()
    assert (encoder.model_name, encoder.revision) == ("fake", "r1")


def test_ac_ing_05_a_tokenizer_without_a_pad_token_is_refused() -> None:
    tokenizer = Tokenizer(models.WordLevel({"the": 0, "[UNK]": 1}, unk_token="[UNK]"))
    with pytest.raises(ValueError, match="PAD"):
        Encoder(FakeSession(), tokenizer, model_name="fake", revision="r1")


def test_ac_ing_05_max_length_is_exposed_so_callers_can_size_chunks_to_fit() -> None:
    encoder, _ = build_encoder(max_length=16)
    assert encoder.max_length == 16
