"""Phase 5 techniques at retrieval time: drop title only chunks, split multi entity questions."""

from __future__ import annotations

import uuid

from docdesk.retrieval.decompose import drug_mentions, sub_queries
from docdesk.retrieval.filters import drop_title_only, is_title_only
from docdesk.retrieval.types import ScoredChunk


def chunk(text: str, title: str = "Propranolol drug label") -> ScoredChunk:
    return ScoredChunk(uuid.uuid4(), uuid.uuid4(), title, text, 0.5, "dense")


def test_ac_ret_01_title_01_a_chunk_that_is_only_the_title_is_title_only() -> None:
    assert is_title_only(chunk("propranolol drug label"))
    assert is_title_only(chunk("Oxycodone hydrochloride drug label ", "Other title"))
    assert is_title_only(chunk("Propranolol Drug Label."))
    assert is_title_only(chunk("Same Words", "same words"))


def test_ac_ret_01_title_02_a_chunk_with_content_is_kept() -> None:
    assert not is_title_only(chunk("Propranolol tablets are available as 10 mg, 20 mg."))
    assert not is_title_only(chunk("the drug label says to store at room temperature away from "
                                   "moisture and light for the whole shelf life of the product"))


def test_ac_ret_01_title_03_dropping_keeps_the_order_of_the_rest() -> None:
    a, b, c = chunk("propranolol drug label"), chunk("real text one"), chunk("real text two")
    assert drop_title_only([a, b, c]) == [b, c]


def test_ac_ret_01_decomp_01_two_drug_names_are_found_in_order_with_their_salt_word() -> None:
    question = "What serious risks do the lithium carbonate and warfarin sodium labels warn about?"
    assert drug_mentions(question) == ["lithium carbonate", "warfarin sodium"]


def test_ac_ret_01_decomp_02_a_multi_drug_question_gets_one_sub_query_per_drug() -> None:
    question = "What serious skin reactions do the lamotrigine and carbamazepine labels warn about?"
    subs = sub_queries(question)
    assert len(subs) == 2
    assert subs[0].startswith("lamotrigine") and "carbamazepine" not in subs[0]
    assert subs[1].startswith("carbamazepine") and "lamotrigine" not in subs[1]
    assert "serious skin reactions" in subs[0] and "serious skin reactions" in subs[1]


def test_ac_ret_01_decomp_03_one_drug_or_none_means_no_split() -> None:
    assert sub_queries("What tablet strengths do propranolol hydrochloride tablets come in?") == []
    assert sub_queries("What causes hemorrhoids, and how can they be treated at home?") == []


def test_ac_ret_01_decomp_04_the_same_drug_twice_is_one_drug() -> None:
    question = "Does warfarin interact with food, and does warfarin need blood tests?"
    assert sub_queries(question) == []
