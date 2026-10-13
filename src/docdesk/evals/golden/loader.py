"""Load golden items from YAML, validate them, and resolve evidence to documents (T081)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import ValidationError

from docdesk.evals.golden.corpus import GoldenCorpus
from docdesk.evals.golden.evidence import QuoteNotFound, check_quote, gold_chunk_ids
from docdesk.evals.golden.schema import GoldenItem


class GoldenValidationError(ValueError):
    """One or more golden problems, all listed so a batch is fixed in one pass."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("\n".join(problems))
        self.problems = problems


class SplitLockedError(PermissionError):
    """The held-out test split is for final reports and the CI baseline only."""


@dataclass(frozen=True)
class ResolvedEvidence:
    """A quote tied to the id of the document it came from."""

    source: str
    document_id: uuid.UUID
    text: str


@dataclass(frozen=True)
class ResolvedItem:
    """A validated item plus its evidence resolved against the corpus."""

    item: GoldenItem
    evidence: tuple[ResolvedEvidence, ...]


def read_items(directory: Path) -> tuple[list[tuple[Path, GoldenItem]], list[str]]:
    """Parse every YAML file with safe_load and the schema; return items and all problems."""
    items: list[tuple[Path, GoldenItem]] = []
    problems: list[str] = []
    for path in sorted(directory.glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as error:
            problems.append(f"{path.name}: not valid YAML ({type(error).__name__})")
            continue
        if not isinstance(data, list):
            problems.append(f"{path.name}: the file must be a list of items")
            continue
        for entry in data:
            items.append((path, parse_item(path, entry, problems)))
    return [(p, i) for p, i in items if i is not None], problems


def parse_item(path: Path, entry: Any, problems: list[str]) -> GoldenItem | None:
    """Validate one entry; a failure is recorded with the file and item id and returns None."""
    name = entry.get("id", "?") if isinstance(entry, dict) else "?"
    try:
        return GoldenItem.model_validate(entry)
    except ValidationError as error:
        details = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in error.errors())
        problems.append(f"{path.name} {name}: {details}")
        return None


def resolve_item(
    item: GoldenItem, corpus: GoldenCorpus, texts: dict[uuid.UUID, str]
) -> ResolvedItem:
    """Resolve source keys to ids and check each quote; raise naming the first problem."""
    resolved = []
    for entry in item.gold_evidence:
        document_id = corpus.document_id(entry.source)
        if document_id is None:
            raise ValueError(f"source {entry.source} matches no document")
        if document_id not in texts:
            texts[document_id] = corpus.cleaned_text(document_id)
        check_quote(texts[document_id], entry.text)
        resolved.append(ResolvedEvidence(entry.source, document_id, entry.text))
    return ResolvedItem(item, tuple(resolved))


def load_golden(
    directory: Path,
    split: Literal["dev", "test"],
    corpus: GoldenCorpus,
    allow_test: bool = False,
) -> list[ResolvedItem]:
    """Load one split, fully validated; the test split needs allow_test=True."""
    if split == "test" and not allow_test:
        raise SplitLockedError("the test split is for final reports only, pass allow_test=True")
    found, problems = read_items(directory)
    seen: set[str] = set()
    for _, item in found:
        if item.id in seen:
            problems.append(f"duplicate id {item.id}")
        seen.add(item.id)
    texts: dict[uuid.UUID, str] = {}
    loaded = []
    for path, item in found:
        try:
            resolved = resolve_item(item, corpus, texts)
        except (ValueError, QuoteNotFound) as error:
            problems.append(f"{path.name} {item.id}: {error}")
            continue
        if item.split == split:
            loaded.append(resolved)
    if problems:
        raise GoldenValidationError(problems)
    return loaded


def gold_sets(resolved: ResolvedItem, corpus: GoldenCorpus) -> list[frozenset[str]]:
    """One set of gold chunk ids per evidence entry, for the retrieval metrics (T087)."""
    sets = []
    for entry in resolved.evidence:
        text = corpus.cleaned_text(entry.document_id)
        chunks = corpus.chunks(entry.document_id)
        sets.append(frozenset(gold_chunk_ids(text, entry.text, chunks)))
    return sets
