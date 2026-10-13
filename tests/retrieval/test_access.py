"""Access filter inside the SQL (AC-RET-05): no leg may return a chunk the user cannot see."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from docdesk.db.models.documents import DocumentStatus
from docdesk.retrieval.dense import dense_search
from docdesk.retrieval.keyword import keyword_search
from fakes.corpus import Corpus, one_hot

pytestmark = pytest.mark.integration


def both_legs(session: Session, user: uuid.UUID) -> set[uuid.UUID]:
    """Ids returned to this user by the dense and the keyword leg together."""
    dense = dense_search(session, one_hot(0), user, top_n=10)
    keyword = keyword_search(session, "aspirin", user, top_n=10)
    return {hit.chunk_id for hit in dense + keyword}


def test_ac_ret_05_another_users_private_chunk_is_never_returned(
    db_session: Session, corpus: Corpus
) -> None:
    alice, bob = corpus.user(), corpus.user()
    corpus.chunk(corpus.document(alice), "aspirin private to alice", hot=0)
    assert both_legs(db_session, bob) == set()


def test_ac_ret_05_the_owner_sees_their_own_chunk(db_session: Session, corpus: Corpus) -> None:
    alice = corpus.user()
    mine = corpus.chunk(corpus.document(alice), "aspirin private to alice", hot=0)
    assert both_legs(db_session, alice) == {mine.id}


def test_ac_ret_05_shared_corpus_chunks_are_visible_to_everyone(
    db_session: Session, corpus: Corpus
) -> None:
    owner, other = corpus.user(), corpus.user()
    shared = corpus.chunk(corpus.document(owner, shared=True), "aspirin public label", hot=0)
    assert both_legs(db_session, other) == {shared.id}


def test_ac_ret_05_chunks_of_documents_that_are_not_ready_are_hidden(
    db_session: Session, corpus: Corpus
) -> None:
    user = corpus.user()
    document = corpus.document(user, status=DocumentStatus.PROCESSING)
    corpus.chunk(document, "aspirin half ingested", hot=0)
    assert both_legs(db_session, user) == set()
