"""Find quotes that sit in more than one document, so gold evidence is never ambiguous."""

from __future__ import annotations

import re
import uuid
from collections.abc import Mapping

from docdesk.evals.golden.corpus import GoldenCorpus
from docdesk.evals.golden.evidence import normalize

LABEL_SUFFIX = re.compile(r"\s*drug label\s*$", re.IGNORECASE)
PARENTHESIS = re.compile(r"^(?P<brand>.*?)\((?P<generic>[^)]*)\)\s*$")


def also_in(quote: str, own_source: str, folded: Mapping[str, str]) -> tuple[str, ...]:
    """Why: a retriever may return another document that says the same words, so list them all."""
    target = normalize(quote)
    others = (key for key, text in folded.items() if key != own_source and target in text)
    return tuple(sorted(others))


def document_names(title: str) -> list[str]:
    """Names a question may use for a document: the brand and the generic name of a label."""
    bare = LABEL_SUFFIX.sub("", title).strip()
    match = PARENTHESIS.match(bare)
    names = [match["brand"], match["generic"]] if match else [bare]
    return [name.strip().lower() for name in names if name.strip()]


def question_names_document(question: str, title: str) -> bool:
    """Why: naming the document in the question is what makes a duplicated quote unambiguous."""
    words = question.lower()
    for name in document_names(title):
        if name in words or (name.endswith("s") and name[:-1] in words):
            return True
    return False


def duplicate_problem(
    question: str,
    also: tuple[str, ...],
    alt_sources: list[str],
    own_title: str,
) -> str | None:
    """Explain what is missing when a quote is duplicated and the item resolves neither way."""
    uncovered = [key for key in also if key not in alt_sources]
    if not uncovered or question_names_document(question, own_title):
        return None
    return (
        f"quote is also in {', '.join(uncovered)}: name the document "
        f"({own_title!r}) in the question or list them in alt_sources"
    )


class CorpusScan:
    """Whitespace folded text of every corpus document, built once and only when needed."""

    def __init__(self, corpus: GoldenCorpus) -> None:
        self._corpus = corpus
        self._folded: dict[str, str] | None = None

    def titles(self) -> dict[str, str]:
        """Source key to title for every document."""
        return self._corpus.source_titles()

    def folded(self) -> dict[str, str]:
        """Source key to folded cleaned text, read once for the whole corpus."""
        if self._folded is None:
            self._folded = {}
            for key in self.titles():
                document_id = self._corpus.document_id(key)
                if document_id is not None:
                    self._folded[key] = normalize(self._corpus.cleaned_text(document_id))
        return self._folded


def resolve_alternate(corpus: GoldenCorpus, scan: CorpusScan, quote: str, key: str) -> uuid.UUID:
    """An alternate must exist and hold the quote, otherwise it would make gold up."""
    document_id = corpus.document_id(key)
    if document_id is None:
        raise ValueError(f"alt source {key} matches no document")
    if normalize(quote) not in scan.folded().get(key, ""):
        raise ValueError(f"alt source {key} does not hold the quote")
    return document_id
