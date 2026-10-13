"""Dense search: nearest chunks by cosine distance (AC-RET-01)."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from docdesk.retrieval.dense import dense_search
from fakes.corpus import Corpus, one_hot

pytestmark = pytest.mark.integration


def test_ac_ret_01_the_closest_chunk_comes_first_with_score_one(
    db_session: Session, corpus: Corpus
) -> None:
    user = corpus.user()
    doc = corpus.document(user, shared=True)
    near = corpus.chunk(doc, "aspirin", hot=0, position=0)
    corpus.chunk(doc, "ibuprofen", hot=1, position=1)
    hits = dense_search(db_session, one_hot(0), user, top_n=2)
    assert hits[0].chunk_id == near.id
    assert hits[0].score == pytest.approx(1.0)
    assert hits[1].score == pytest.approx(0.0)
    assert hits[0].source == "dense"


def test_ac_ret_01_top_n_limits_the_number_of_results(db_session: Session, corpus: Corpus) -> None:
    user = corpus.user()
    doc = corpus.document(user)
    for i in range(4):
        corpus.chunk(doc, f"text {i}", hot=i, position=i)
    assert len(dense_search(db_session, one_hot(0), user, top_n=3)) == 3


def test_ac_ret_01_a_hit_carries_its_document_title_and_text(
    db_session: Session, corpus: Corpus
) -> None:
    user = corpus.user()
    doc = corpus.document(user, title="Aspirin label")
    row = corpus.chunk(doc, "aspirin", hot=0)
    hit = dense_search(db_session, one_hot(0), user, top_n=1)[0]
    assert (hit.document_id, hit.document_title, hit.text) == (doc.id, "Aspirin label", row.text)


def test_ac_ret_01_a_user_with_no_documents_gets_an_empty_list(
    db_session: Session, corpus: Corpus
) -> None:
    assert dense_search(db_session, one_hot(0), corpus.user(), top_n=5) == []
