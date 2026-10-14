"""T101 (AC-EVL-06): CI downloads the embedding model at a pinned revision and checks its hash."""

from __future__ import annotations

import hashlib
import sys
import tomllib
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import fetch_model  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def fake_client(bodies: dict[str, bytes]) -> httpx.Client:
    """A client that answers from a dict by file path and records nothing on the network."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path.split("/resolve/")[1].split("/", 1)[1]
        return httpx.Response(200, content=bodies[path])

    return httpx.Client(transport=httpx.MockTransport(handler))


def pins_for(bodies: dict[str, bytes]) -> dict[str, str]:
    """The sha256 table a fake download should be checked against."""
    return {name: hashlib.sha256(data).hexdigest() for name, data in bodies.items()}


BODIES = {"onnx/model.onnx": b"model bytes", "tokenizer.json": b"{}"}


def test_ac_evl_06_pinned_revision_is_the_one_b0_uses() -> None:
    config = tomllib.loads((ROOT / "evals" / "configs" / "b0.toml").read_text(encoding="utf-8"))
    assert fetch_model.REVISION == config["embedding"]["revision"]


def test_ac_evl_06_every_model_file_has_a_sha256_pin() -> None:
    assert set(fetch_model.SHA256) == {"onnx/model.onnx", "tokenizer.json"}
    assert all(len(value) == 64 for value in fetch_model.SHA256.values())


def test_ac_evl_06_download_writes_files_and_revision(tmp_path: Path) -> None:
    fetch_model.fetch_model(tmp_path, fake_client(BODIES), pins_for(BODIES))
    assert (tmp_path / "onnx" / "model.onnx").read_bytes() == b"model bytes"
    assert (tmp_path / "tokenizer.json").read_bytes() == b"{}"
    assert (tmp_path / "REVISION").read_text(encoding="utf-8").strip() == fetch_model.REVISION


def test_ac_evl_06_a_file_with_the_wrong_hash_is_refused_and_not_kept(tmp_path: Path) -> None:
    wrong = {**pins_for(BODIES), "tokenizer.json": "0" * 64}
    with pytest.raises(ValueError, match="tokenizer.json"):
        fetch_model.fetch_model(tmp_path, fake_client(BODIES), wrong)
    assert not (tmp_path / "tokenizer.json").exists()
    assert not (tmp_path / "REVISION").exists()


def test_ac_evl_06_files_that_already_match_are_not_downloaded_again(tmp_path: Path) -> None:
    fetch_model.fetch_model(tmp_path, fake_client(BODIES), pins_for(BODIES))
    refusing = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500)))
    fetch_model.fetch_model(tmp_path, refusing, pins_for(BODIES))
