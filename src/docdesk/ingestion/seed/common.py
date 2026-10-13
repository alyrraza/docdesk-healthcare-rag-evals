"""Shared seed helpers: a document type, a safe download folder and a manifest of what was saved."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

MANIFEST_NAME = "manifest.json"


class SeedFetchError(Exception):
    """A public source answered with an error or could not be reached."""


@dataclass(frozen=True)
class SeedDocument:
    """One public document ready to be ingested as a shared corpus document."""

    source_id: str
    title: str
    text: str
    source_url: str
    query: str = ""


def ensure_download_dir(path: Path, project_root: Path) -> Path:
    """Refuse download folders outside data/ and .cache/, since the system drive is full."""
    resolved = path.resolve()
    allowed = [(project_root / "data").resolve(), (project_root / ".cache").resolve()]
    if not any(resolved.is_relative_to(root) for root in allowed):
        raise ValueError(f"downloads must go under data/ or .cache/, not {resolved}")
    return resolved


def load_manifest(directory: Path) -> dict[str, dict[str, str]]:
    """Read the record of saved documents; a corrupt file raises instead of being ignored."""
    path = directory / MANIFEST_NAME
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_document(directory: Path, document: SeedDocument) -> Path:
    """Write the text and record it in the manifest, using a file name that cannot escape."""
    directory.mkdir(parents=True, exist_ok=True)
    file_name = re.sub(r"[^A-Za-z0-9_-]", "_", document.source_id) + ".txt"
    path = directory / file_name
    path.write_text(document.text, encoding="utf-8")
    manifest = load_manifest(directory)
    manifest[document.source_id] = {
        "title": document.title,
        "source_url": document.source_url,
        "query": document.query,
        "file": file_name,
    }
    (directory / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path
