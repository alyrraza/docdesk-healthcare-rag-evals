"""The packer fits evidence into the budget, lowest ranked dropped first (AC-CTX-01, AC-CTX-02)."""

from __future__ import annotations

import random
import uuid

from docdesk.context.packer import SEPARATOR_TOKENS, pack
from docdesk.retrieval.types import ScoredChunk
from fakes.ingestion import WordCounter

COUNTER = WordCounter()


def chunk(n: int, words: int = 10, doc: int | None = None, text: str | None = None) -> ScoredChunk:
    body = text if text is not None else " ".join(f"w{n}x{i}" for i in range(words))
    return ScoredChunk(
        chunk_id=uuid.UUID(int=n),
        document_id=uuid.UUID(int=1000 + (n if doc is None else doc)),
        document_title=f"Doc{n}",
        text=body,
        score=1.0 / n,
        source="dense",
    )


def test_ac_ctx_01_everything_that_fits_is_packed_in_rank_order_with_short_labels() -> None:
    result = pack([chunk(1), chunk(2), chunk(3)], 1000, COUNTER)
    assert [item.label for item in result.items] == ["c1", "c2", "c3"]
    assert [item.chunk.chunk_id.int for item in result.items] == [1, 2, 3]
    assert result.evidence_text.startswith("[c1] Doc1\n")
    assert result.dropped == []


def test_ac_ctx_02_when_evidence_does_not_fit_the_lowest_ranked_are_dropped_first() -> None:
    # One item is "[cN] DocN" (2 words) plus 10 words plus the separator allowance.
    each = 2 + 10 + SEPARATOR_TOKENS
    result = pack([chunk(i, words=10) for i in range(1, 6)], 3 * each + 5, COUNTER)
    kept = [item.chunk.chunk_id.int for item in result.items]
    assert kept == list(range(1, len(kept) + 1))
    assert len(kept) == 3
    assert [d.chunk_id.int for d in result.dropped] == [4, 5]
    assert {d.reason for d in result.dropped} == {"budget"}


def test_ac_ctx_02_dropped_ids_are_recorded_for_the_trace() -> None:
    result = pack([chunk(1), chunk(2)], 15, COUNTER)
    assert result.dropped_ids == [uuid.UUID(int=2)]
    assert result.used_ids == [uuid.UUID(int=1)]


def test_ac_ctx_01_a_chunk_is_never_cut_in_half() -> None:
    result = pack([chunk(1, words=50)], 30, COUNTER)
    assert result.items == []
    assert result.dropped[0].reason == "budget"


def test_ac_ctx_01_packed_evidence_never_exceeds_the_budget_for_random_inputs() -> None:
    rng = random.Random(11)
    for _ in range(300):
        chunks = [chunk(n, words=rng.randint(1, 120)) for n in range(1, rng.randint(1, 15))]
        budget = rng.randint(0, 600)
        result = pack(chunks, budget, COUNTER)
        assert COUNTER.count(result.evidence_text) <= budget
        assert result.tokens <= budget
        assert len(result.items) + len(result.dropped) == len(chunks)


def test_ac_ctx_02_the_kept_items_are_always_a_prefix_of_the_ranking() -> None:
    rng = random.Random(5)
    for _ in range(200):
        chunks = [chunk(n, words=rng.randint(1, 80)) for n in range(1, 10)]
        result = pack(chunks, rng.randint(0, 400), COUNTER)
        assert [i.chunk.chunk_id.int for i in result.items] == list(range(1, len(result.items) + 1))


def test_ac_ctx_01_chunks_below_the_relevance_threshold_are_left_out_and_recorded() -> None:
    result = pack([chunk(1), chunk(4)], 1000, COUNTER, min_score=0.5)
    assert [i.chunk.chunk_id.int for i in result.items] == [1]
    assert [(d.chunk_id.int, d.reason) for d in result.dropped] == [(4, "below_threshold")]


def test_ac_ctx_01_a_near_duplicate_from_the_same_document_is_dropped() -> None:
    a = chunk(1, doc=7, text="aspirin may cause stomach bleeding in some adults today")
    b = chunk(2, doc=7, text="aspirin may cause stomach bleeding in some adults")
    result = pack([a, b], 1000, COUNTER)
    assert [i.chunk.chunk_id.int for i in result.items] == [1]
    assert result.dropped[0].reason == "duplicate"


def test_ac_ctx_01_the_same_text_in_different_documents_is_kept() -> None:
    a = chunk(1, doc=7, text="same words in two places")
    b = chunk(2, doc=8, text="same words in two places")
    assert len(pack([a, b], 1000, COUNTER).items) == 2


def test_ac_ctx_01_one_document_cannot_crowd_out_the_others() -> None:
    chunks = [chunk(n, doc=7) for n in range(1, 5)] + [chunk(5, doc=8)]
    result = pack(chunks, 1000, COUNTER, max_per_document=2)
    assert [i.chunk.chunk_id.int for i in result.items] == [1, 2, 5]
    assert {d.reason for d in result.dropped} == {"document_cap"}


def test_ac_ctx_01_nothing_to_pack_gives_an_empty_pack() -> None:
    result = pack([], 1000, COUNTER)
    assert result.items == [] and result.evidence_text == "" and result.tokens == 0
