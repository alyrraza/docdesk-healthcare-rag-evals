"""Download the pinned embedding model for CI or a fresh clone (T101). No token, no secret.

Usage (project root):
    python scripts/fetch_model.py [--dest .cache/models/all-MiniLM-L6-v2]
The revision matches evals/configs/b0.toml. Every file is checked against a sha256 pin before
anything is written, and files that already match are left alone.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import httpx

REPO = "sentence-transformers/all-MiniLM-L6-v2"
REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
SHA256 = {
    "onnx/model.onnx": "6fd5d72fe4589f189f8ebc006442dbb529bb7ce38f8082112682524616046452",
    "tokenizer.json": "be50c3628f2bf5bb5e3a7f17b1f74611b2561a3a27eeab05e5aa30f411572037",
}
DEFAULT_DEST = Path(".cache/models/all-MiniLM-L6-v2")


def digest(data: bytes) -> str:
    """Why: one place decides how a file is hashed, for the pin check and the skip check."""
    return hashlib.sha256(data).hexdigest()


def is_current(dest: Path, pins: dict[str, str]) -> bool:
    """Why: a rerun in CI or on a laptop should not download 90 MB it already has."""
    revision = dest / "REVISION"
    if not revision.is_file() or revision.read_text(encoding="utf-8").strip() != REVISION:
        return False
    return all(
        (dest / name).is_file() and digest((dest / name).read_bytes()) == pin
        for name, pin in pins.items()
    )


def fetch_model(dest: Path, client: httpx.Client, pins: dict[str, str] = SHA256) -> None:
    """Why: CI has no model folder, and an unverified download must never reach the encoder."""
    if is_current(dest, pins):
        return
    downloaded: dict[str, bytes] = {}
    for name, pin in pins.items():
        response = client.get(f"https://huggingface.co/{REPO}/resolve/{REVISION}/{name}")
        response.raise_for_status()
        if digest(response.content) != pin:
            raise ValueError(f"{name}: sha256 does not match the pin for revision {REVISION}")
        downloaded[name] = response.content
    for name, data in downloaded.items():
        target = dest / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (dest / "REVISION").write_text(REVISION + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    with httpx.Client(follow_redirects=True, timeout=120) as http:
        fetch_model(parser.parse_args().dest, http)
    print("model ready")
