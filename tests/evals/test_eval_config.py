"""B0 is pinned in one file with a content hash, so a silent edit cannot move the baseline."""

from __future__ import annotations

from pathlib import Path

import pytest

from docdesk.context.budget import ContextBudget
from docdesk.core.config import Settings
from docdesk.evals.config import ConfigHashMismatch, content_hash, load_eval_config

B0_PATH = Path(__file__).resolve().parents[2] / "evals" / "configs" / "b0.toml"

SMALL = """
id = "t0"
content_hash = "{hash}"

[retrieval]
mode = "dense"
top_k = 5
"""


def write_small(tmp_path: Path, hash_value: str) -> Path:
    path = tmp_path / "t0.toml"
    path.write_text(SMALL.format(hash=hash_value), encoding="utf-8")
    return path


def test_t079e_the_shipped_b0_file_matches_its_own_hash() -> None:
    config = load_eval_config(B0_PATH)
    assert config.id == "b0"
    assert len(config.content_hash) == 64


def test_t079e_editing_any_value_without_a_new_hash_is_refused(tmp_path: Path) -> None:
    good = content_hash({"id": "t0", "retrieval": {"mode": "dense", "top_k": 5}})
    load_eval_config(write_small(tmp_path, good))
    edited = write_small(tmp_path, good)
    edited.write_text(edited.read_text(encoding="utf-8").replace("top_k = 5", "top_k = 6"))
    with pytest.raises(ConfigHashMismatch):
        load_eval_config(edited)


def test_t079e_comments_and_key_order_do_not_change_the_hash() -> None:
    first = content_hash({"a": 1, "b": {"c": 2, "d": 3}})
    second = content_hash({"b": {"d": 3, "c": 2}, "a": 1})
    assert first == second


def test_t079e_the_hash_does_not_include_itself() -> None:
    base = {"id": "t0", "x": 1}
    assert content_hash(base) == content_hash({**base, "content_hash": "anything"})


def test_t079e_b0_is_dense_top_5_with_no_rerank() -> None:
    config = load_eval_config(B0_PATH)
    retrieval = config.retrieval_config()
    assert (retrieval.mode, retrieval.top_k) == ("dense", 5)
    assert retrieval.config_id == "dense-n20-k5-rrf60"
    assert config.values["rerank"]["enabled"] is False


def test_t079e_b0_context_budget_matches_the_live_default() -> None:
    config = load_eval_config(B0_PATH)
    assert config.context_budget() == ContextBudget()


def test_t079e_b0_models_match_the_settings_defaults() -> None:
    values = load_eval_config(B0_PATH).values["models"]
    assert values["generator"] == Settings.model_fields["generator_model"].default
    assert values["judge"] == Settings.model_fields["judge_model"].default


def test_t079e_b0_records_the_chunking_prompt_and_abstain_pins() -> None:
    values = load_eval_config(B0_PATH).values
    assert values["chunking"] == {"strategy": "recursive", "size": 200, "overlap": 40}
    prompt = values["prompt"]
    assert (prompt["name"], prompt["version"]) == ("answer", "1.0.0")
    assert set(prompt) == {"name", "version", "content_hash"}
    assert values["packer"]["max_per_document"] == 2
    assert values["abstain"]["threshold"] == 0.0


def test_t080a_b0_gives_the_ingest_settings_the_corpus_must_be_built_with() -> None:
    ingest = load_eval_config(B0_PATH).ingest_config()
    assert (ingest.chunker, ingest.size, ingest.overlap) == ("recursive", 200, 40)


def test_t080a_b0_fingerprint_uses_the_same_model_string_the_chunks_store() -> None:
    fingerprint = load_eval_config(B0_PATH).corpus_fingerprint()
    revision = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
    assert fingerprint.embedding_model == f"all-MiniLM-L6-v2@{revision}"
    assert (fingerprint.chunker, fingerprint.chunk_size, fingerprint.overlap) == (
        "recursive",
        200,
        40,
    )
