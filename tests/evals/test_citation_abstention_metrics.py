"""T092: citation precision and recall, and abstain versus refuse counts, without any LLM."""

from __future__ import annotations

from docdesk.evals.golden.evidence import gold_chunk_ids
from docdesk.evals.metrics.abstention import count_cells
from docdesk.evals.metrics.citation import citation_scores
from docdesk.evals.outcome import outcome_cell

DOC = "Alpha one two three four five six seven eight nine ten. Beta eleven twelve thirteen."
QUOTE = "one two three four five six seven eight nine ten"


def chunk_gold(*chunk_texts: str) -> set[str]:
    chunks = [(f"c{i}", text) for i, text in enumerate(chunk_texts)]
    return gold_chunk_ids(DOC, QUOTE, chunks)


def test_ac_evl_02_cite_01_resolver_rule_whole_quote_or_half_overlap() -> None:
    whole = "Alpha one two three four five six seven eight nine ten."
    half = "Alpha one two three four five six"  # overlaps 6 of the quote's 10 words
    small = "Alpha one two"
    assert chunk_gold(whole) == {"c0"}
    assert chunk_gold(half) == {"c0"}
    assert chunk_gold(small) == set()


def test_ac_evl_02_cite_02_precision_and_recall_from_gold_sets() -> None:
    gold = [{"a", "b"}, {"c"}]
    scores = citation_scores(["a", "x", "c", "y"], gold)
    assert scores.precision == 0.5
    assert scores.recall == 1.0


def test_ac_evl_02_cite_03_duplicate_citations_count_once() -> None:
    scores = citation_scores(["a", "a", "x"], [{"a"}])
    assert scores.precision == 0.5


def test_ac_evl_02_cite_04_no_citation_has_no_precision_and_zero_recall() -> None:
    scores = citation_scores([], [{"a"}])
    assert scores.precision is None
    assert scores.recall == 0.0


def test_ac_evl_02_cite_05_no_gold_has_no_citation_scores() -> None:
    scores = citation_scores(["a"], [])
    assert scores.precision is None and scores.recall is None


def test_ac_evl_03_abstain_01_every_pair_lands_in_one_cell() -> None:
    table = {
        ("answer", "answered"): "correct_answer",
        ("answer", "abstained"): "wrong_abstain",
        ("answer", "refused"): "wrong_refusal",
        ("abstain", "abstained"): "correct_abstain",
        ("abstain", "answered"): "missed_abstain",
        ("abstain", "refused"): "wrong_refusal",
        ("refuse", "refused"): "correct_refusal",
        ("refuse", "answered"): "missed_refusal",
        ("refuse", "abstained"): "missed_refusal",
    }
    for (behavior, outcome), cell in table.items():
        assert outcome_cell(behavior, outcome) == cell
    for behavior in ("answer", "abstain", "refuse"):
        assert outcome_cell(behavior, "error") == "error"


def test_ac_evl_03_abstain_02_abstain_and_refuse_are_counted_separately() -> None:
    pairs = [
        ("abstain", "abstained"), ("abstain", "abstained"), ("abstain", "answered"),
        ("answer", "abstained"), ("refuse", "refused"), ("refuse", "answered"),
        ("answer", "refused"), ("answer", "answered"), ("answer", "error"),
    ]
    counts = count_cells(pairs)
    assert (counts.correct_abstain, counts.wrong_abstain, counts.missed_abstain) == (2, 1, 1)
    assert (counts.correct_refusal, counts.wrong_refusal, counts.missed_refusal) == (1, 1, 1)
    assert counts.correct_answer == 1 and counts.errors == 1


def test_ac_evl_03_abstain_03_rates_use_their_own_counts() -> None:
    counts = count_cells([("abstain", "abstained"), ("abstain", "answered"),
                          ("answer", "abstained"), ("refuse", "refused")])
    assert counts.abstain_recall == 0.5
    assert counts.abstain_precision == 0.5
    assert counts.refusal_recall == 1.0
    assert count_cells([]).abstain_recall is None
