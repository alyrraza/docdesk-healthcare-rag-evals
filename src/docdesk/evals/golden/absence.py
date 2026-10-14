"""Prove by code that an unanswerable item's key terms are not in the corpus (AC-EVL-01)."""

from __future__ import annotations

from docdesk.evals.golden.corpus import GoldenCorpus
from docdesk.evals.golden.duplicates import CorpusScan
from docdesk.evals.golden.evidence import normalize
from docdesk.evals.golden.schema import GoldenItem


def fold(text: str) -> str:
    """Why: terms and documents are compared with whitespace folded and case ignored."""
    return normalize(text).casefold()


def scope_texts(item: GoldenItem, corpus: GoldenCorpus, scan: CorpusScan) -> dict[str, str]:
    """The folded text of each document the item's absence claim covers, by source key."""
    if item.absence_scope == "corpus":
        return {key: fold(text) for key, text in scan.folded().items()}
    key = item.absence_scope or ""
    document_id = corpus.document_id(key)
    if document_id is None:
        raise ValueError(f"absence_scope {key} matches no document")
    return {key: fold(corpus.cleaned_text(document_id))}


def absence_problems(item: GoldenItem, corpus: GoldenCorpus, scan: CorpusScan) -> list[str]:
    """Why: a term found in the scope means the corpus might answer, so the item would be wrong."""
    if not item.absent_terms:
        return []
    try:
        texts = scope_texts(item, corpus, scan)
    except ValueError as error:
        return [str(error)]
    problems = []
    for term in item.absent_terms:
        wanted = fold(term)
        holders = sorted(key for key, text in texts.items() if wanted in text)
        if holders:
            problems.append(f"absent term {term!r} occurs in {', '.join(holders[:3])}")
    return problems
