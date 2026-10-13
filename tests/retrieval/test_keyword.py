"""Keyword search: Postgres full text search ranked by ts_rank_cd (AC-RET-02)."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from docdesk.retrieval.keyword import keyword_search
from fakes.corpus import Corpus

pytestmark = pytest.mark.integration


def test_ac_ret_02_only_chunks_containing_the_term_are_returned(
    db_session: Session, corpus: Corpus
) -> None:
    user = corpus.user()
    doc = corpus.document(user)
    hit = corpus.chunk(doc, "Warfarin raises bleeding risk.", hot=0, position=0)
    corpus.chunk(doc, "Aspirin relieves pain.", hot=1, position=1)
    results = keyword_search(db_session, "warfarin", user, top_n=5)
    assert [r.chunk_id for r in results] == [hit.id]
    assert results[0].source == "keyword"
    assert results[0].score > 0


def test_ac_ret_02_stemming_matches_word_forms(db_session: Session, corpus: Corpus) -> None:
    user = corpus.user()
    hit = corpus.chunk(corpus.document(user), "Patients reported dizziness.", hot=0)
    assert [r.chunk_id for r in keyword_search(db_session, "patient", user, top_n=5)] == [hit.id]


def test_ac_ret_02_the_chunk_with_more_matching_terms_ranks_first(
    db_session: Session, corpus: Corpus
) -> None:
    user = corpus.user()
    doc = corpus.document(user)
    corpus.chunk(doc, "Aspirin is a reliever.", hot=0, position=0)
    best = corpus.chunk(doc, "Aspirin pain and aspirin fever and pain.", hot=1, position=1)
    results = keyword_search(db_session, "aspirin pain", user, top_n=5)
    assert results[0].chunk_id == best.id


def test_ac_ret_02_a_query_of_only_stop_words_returns_nothing_not_an_error(
    db_session: Session, corpus: Corpus
) -> None:
    user = corpus.user()
    corpus.chunk(corpus.document(user), "the of and", hot=0)
    assert keyword_search(db_session, "the of and", user, top_n=5) == []


def test_ac_ret_02_punctuation_and_operators_in_a_question_do_not_break_the_query(
    db_session: Session, corpus: Corpus
) -> None:
    user = corpus.user()
    hit = corpus.chunk(corpus.document(user), "Aspirin side effects", hot=0)
    question = "What are aspirin's side-effects?! (adults) & | :*"
    results = keyword_search(db_session, question, user, top_n=5)
    assert hit.id in [r.chunk_id for r in results]
