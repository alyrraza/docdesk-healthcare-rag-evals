"""Load golden items from YAML, validate them, and resolve evidence to documents (T081)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import ValidationError

from docdesk.evals.golden.corpus import GoldenCorpus
from docdesk.evals.golden.counts import ItemCounts, count_found
from docdesk.evals.golden.duplicates import (
    CorpusScan,
    also_in,
    duplicate_problem,
    resolve_alternate,
)
from docdesk.evals.golden.evidence import (
    ChunkNotLocated,
    QuoteNotFound,
    check_quote,
    gold_chunk_ids,
)
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
    alt_document_ids: tuple[uuid.UUID, ...] = ()
    also_in: tuple[str, ...] = ()


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
        found, issues = read_file(path)
        items += [(path, item) for item in found]
        problems += issues
    return items, problems


def read_file(path: Path) -> tuple[list[GoldenItem], list[str]]:
    """Parse one YAML file only, so one batch can be handled while another is unfinished."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        return [], [f"{path.name}: not valid YAML ({type(error).__name__})"]
    if not isinstance(data, list):
        return [], [f"{path.name}: the file must be a list of items"]
    problems: list[str] = []
    parsed = [parse_item(path, entry, problems) for entry in data]
    return [item for item in parsed if item is not None], problems


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
    item: GoldenItem, corpus: GoldenCorpus, texts: dict[uuid.UUID, str], scan: CorpusScan
) -> ResolvedItem:
    """Resolve source keys to ids, check each quote and its alternates; raise naming the problem."""
    resolved = []
    for entry in item.gold_evidence:
        document_id = corpus.document_id(entry.source)
        if document_id is None:
            raise ValueError(f"source {entry.source} matches no document")
        if document_id not in texts:
            texts[document_id] = corpus.cleaned_text(document_id)
        check_quote(texts[document_id], entry.text)
        alts = tuple(resolve_alternate(corpus, scan, entry.text, key) for key in entry.alt_sources)
        found = also_in(entry.text, entry.source, scan.folded())
        title = scan.titles().get(entry.source, entry.source)
        if problem := duplicate_problem(item.question, found, entry.alt_sources, title):
            raise ValueError(problem)
        resolved.append(ResolvedEvidence(entry.source, document_id, entry.text, alts, found))
    return ResolvedItem(item, tuple(resolved))


def check_distinct_chunks(resolved: ResolvedItem, corpus: GoldenCorpus) -> None:
    """Every quote needs a gold chunk, and a multi chunk item needs a different one per quote."""
    sets = gold_sets(resolved, corpus)
    for entry, chunk_ids in zip(resolved.evidence, sets, strict=True):
        if not chunk_ids:
            raise ValueError(f"no chunk is gold for the quote {entry.text[:40]!r}")
    if resolved.item.type != "multi_chunk":
        return
    for first in range(len(sets)):
        for second in range(first + 1, len(sets)):
            if sets[first] & sets[second]:
                raise ValueError(f"quotes {first + 1} and {second + 1} land in the same chunk")


def load_golden(
    directory: Path,
    split: Literal["dev", "test"],
    corpus: GoldenCorpus,
    allow_test: bool = False,
    include_drafts: bool = False,
) -> list[ResolvedItem]:
    """Load one split, fully validated; drafts and the test split each need an explicit flag."""
    if split == "test" and not allow_test:
        raise SplitLockedError("the test split is for final reports only, pass allow_test=True")
    found, problems = read_items(directory)
    seen: set[str] = set()
    for _, item in found:
        if item.id in seen:
            problems.append(f"duplicate id {item.id}")
        seen.add(item.id)
    texts: dict[uuid.UUID, str] = {}
    scan = CorpusScan(corpus)
    loaded = []
    for path, item in found:
        try:
            resolved = resolve_item(item, corpus, texts, scan)
            check_distinct_chunks(resolved, corpus)
        except (ValueError, QuoteNotFound, ChunkNotLocated) as error:
            problems.append(f"{path.name} {item.id}: {error}")
            continue
        if item.split == split and (item.verified or include_drafts):
            loaded.append(resolved)
    if problems:
        raise GoldenValidationError(problems)
    return loaded


def count_items(directory: Path) -> ItemCounts:
    """Count verified and unverified items from the schema alone; raises on schema problems."""
    found, problems = read_items(directory)
    if problems:
        raise GoldenValidationError(problems)
    return count_found([item for _, item in found])


def gold_sets(resolved: ResolvedItem, corpus: GoldenCorpus) -> list[frozenset[str]]:
    """One set of gold chunk ids per evidence entry, for the retrieval metrics (T087)."""
    sets = []
    for entry in resolved.evidence:
        gold: set[str] = set()
        for document_id in (entry.document_id, *entry.alt_document_ids):
            text = corpus.cleaned_text(document_id)
            gold |= gold_chunk_ids(text, entry.text, corpus.chunks(document_id))
        sets.append(frozenset(gold))
    return sets
