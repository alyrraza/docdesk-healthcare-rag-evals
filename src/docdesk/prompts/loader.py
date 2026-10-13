"""Reads prompt files: front matter, the system and user sections, and a content hash."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

STATUSES = ("draft", "released", "retired")
REQUIRED_KEYS = ("name", "version", "schema", "params", "status", "changelog")


class PromptError(ValueError):
    """A prompt file that cannot be used, with the reason."""


@dataclass(frozen=True)
class PromptFile:
    """One prompt version as plain data."""

    name: str
    version: str
    schema: str
    params: dict[str, Any]
    untrusted: tuple[str, ...]
    status: str
    changelog: str
    system: str
    user: str
    content_hash: str
    # The normalized file text, stored in the database so a version can be rebuilt from it.
    text: str


def scalar(raw: str) -> Any:
    """Turn a front matter value into an int, a float or a string without quotes."""
    value = re.sub(r"\s+#.*$", "", raw).strip().strip("\"'")
    for convert in (int, float):
        try:
            return convert(value)
        except ValueError:
            continue
    return value


def parse_front_matter(lines: list[str]) -> dict[str, Any]:
    """Read the small subset of YAML our prompt files use: scalars, one level dicts and lists."""
    data: dict[str, Any] = {}
    key: str | None = None
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith(" "):
            name, _, rest = line.partition(":")
            key = name.strip()
            data[key] = [] if rest.strip() == "[]" else (scalar(rest) if rest.strip() else None)
        elif key is not None and line.strip().startswith("- "):
            data[key] = [*(data[key] or []), scalar(line.strip()[2:])]
        elif key is not None:
            name, _, rest = line.strip().partition(":")
            data[key] = {**(data[key] or {}), name.strip(): scalar(rest)}
    return data


def parse_prompt(raw: str) -> PromptFile:
    """Build a PromptFile from file text, or say exactly what is wrong with it."""
    text = raw.replace("\r\n", "\n")
    if not text.startswith("---\n") or "\n---\n" not in text[4:] + "\n":
        raise PromptError("the file must start with a front matter block between --- lines")
    head, _, body = text[4:].partition("\n---\n")
    meta = parse_front_matter(head.split("\n"))
    for key in REQUIRED_KEYS:
        if meta.get(key) in (None, ""):
            raise PromptError(f"front matter is missing '{key}'")
    if meta["status"] not in STATUSES:
        raise PromptError(f"status must be one of {', '.join(STATUSES)}, got '{meta['status']}'")
    sections = dict(re.findall(r"^## (system|user)\n(.*?)(?=^## |\Z)", body, re.S | re.M))
    for section in ("system", "user"):
        if not sections.get(section, "").strip():
            raise PromptError(f"the file needs a non empty '## {section}' section")
    return PromptFile(
        name=str(meta["name"]),
        version=str(meta["version"]),
        schema=str(meta["schema"]),
        params=dict(meta["params"]),
        untrusted=tuple(meta.get("untrusted") or ()),
        status=str(meta["status"]),
        changelog=str(meta["changelog"]),
        system=sections["system"].strip(),
        user=sections["user"].strip(),
        content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        text=text,
    )


def load_prompt(path: Path) -> PromptFile:
    """Read one file from disk, naming the file in any error."""
    try:
        return parse_prompt(path.read_text(encoding="utf-8"))
    except PromptError as error:
        raise PromptError(f"{path.name}: {error}") from error


def load_all(directory: Path) -> list[PromptFile]:
    """Load every prompts/<name>/<name>.v<N>.md file, in a stable order."""
    return [load_prompt(path) for path in sorted(directory.glob("*/*.md"))]
