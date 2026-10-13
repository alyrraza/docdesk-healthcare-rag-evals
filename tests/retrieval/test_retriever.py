"""The retriever runs the stages a config asks for and reports how long each took."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from docdesk.retrieval.retriever import retrieve
from docdesk.retrieval.types import RetrievalConfig
from fakes.corpus import Corpus, FixedEncoder

pytestmark = pytest.mark.integration


def build(corpus: Corpus):
    """A user with three chunks: one near in meaning, one holding the keyword, one unrelated."""
    user = corpus.user()
    doc = corpus.document(user, shared=True)
    near = corpus.chunk(doc, "Gastric irritation is common.", hot=0, position=0)
    word = corpus.chunk(doc, "Warfarin interacts with aspirin.", hot=5, position=1)
    corpus.chunk(doc, "Unrelated filler text.", hot=9, position=2)
    return user, near, word


def test_ac_ret_01_dense_mode_returns_only_the_dense_leg(
    db_session: Session, corpus: Corpus
) -> None:
    user, near, _ = build(corpus)
    config = RetrievalConfig(mode="dense", top_n=3, top_k=2)
    result = retrieve(db_session, FixedEncoder(0), "aspirin", user, config)
    assert result.chunks[0].chunk_id == near.id
    assert {c.source for c in result.chunks} == {"dense"}
    assert len(result.chunks) == 2


def test_ac_ret_02_keyword_mode_returns_only_the_keyword_leg(
    db_session: Session, corpus: Corpus
) -> None:
    user, _, word = build(corpus)
    result = retrieve(db_session, FixedEncoder(0), "aspirin", user, RetrievalConfig(mode="keyword"))
    assert [c.chunk_id for c in result.chunks] == [word.id]


def test_ac_ret_03_hybrid_mode_fuses_both_legs_and_keeps_top_k(
    db_session: Session, corpus: Corpus
) -> None:
    user, near, word = build(corpus)
    config = RetrievalConfig(mode="hybrid", top_n=3, top_k=2)
    result = retrieve(db_session, FixedEncoder(0), "aspirin", user, config)
    assert {c.chunk_id for c in result.chunks} == {near.id, word.id}
    assert len(result.chunks) == 2


def test_ac_ret_03_the_result_names_its_config_and_the_stage_timings(
    db_session: Session, corpus: Corpus
) -> None:
    user, _, _ = build(corpus)
    config = RetrievalConfig()
    result = retrieve(db_session, FixedEncoder(0), "aspirin", user, config)
    assert result.config_id == config.config_id == "hybrid-n20-k5-rrf60"
    assert set(result.timings_ms) == {"embed", "dense", "keyword", "fuse", "total"}
    assert all(ms >= 0 for ms in result.timings_ms.values())


def test_ac_ret_01_dense_mode_does_not_run_the_keyword_leg(
    db_session: Session, corpus: Corpus
) -> None:
    user, _, _ = build(corpus)
    result = retrieve(db_session, FixedEncoder(0), "aspirin", user, RetrievalConfig(mode="dense"))
    assert "keyword" not in result.timings_ms


def test_ac_ret_01_an_empty_corpus_gives_an_empty_result_with_score_zero(
    db_session: Session, corpus: Corpus
) -> None:
    result = retrieve(db_session, FixedEncoder(0), "aspirin", corpus.user(), RetrievalConfig())
    assert result.chunks == []
    assert result.best_score == 0.0


def test_ac_ret_03_the_best_score_is_the_first_chunks_score(
    db_session: Session, corpus: Corpus
) -> None:
    user, _, _ = build(corpus)
    result = retrieve(db_session, FixedEncoder(0), "aspirin", user, RetrievalConfig())
    assert result.best_score == result.chunks[0].score > 0
