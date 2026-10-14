"""T099 (AC-EVL-07): synthetic calibration outputs are built by fixed, seeded, checked rules."""

from __future__ import annotations

from datetime import date

from docdesk.evals.calib_sample import Output, answer_hash
from docdesk.evals.calib_synth import (
    Candidate,
    Parent,
    build_synthetic,
    drug_of,
    manifest_synthetic,
)
from docdesk.evals.calib_synth_text import CONNECTOR


def parent(item_id: str, kind: str, answer: str, keys: int = 2, drug: str = "alphadrug",
           used: tuple[str, ...] = ("ch-a",), run: str = "run-1") -> Parent:
    output = Output(run, item_id, kind, answer, used)
    return Parent(output, f"Question about {drug}?", keys, frozenset({drug}))


def candidate(chunk_id: str, drug: str, text: str, source: str | None = None) -> Candidate:
    return Candidate(chunk_id, source or f"seed:openfda:{drug}", drug, text)


DOSE = "The usual adult dose is {n} mg twice daily and rises slowly."
CANDIDATES = [candidate(f"ch-{d}", d, DOSE.format(n=i + 5)) for i, d in
              enumerate(["betadrug", "gammadrug", "deltadrug", "epsilondrug", "zetadrug",
                         "etadrug", "thetadrug"])]
PARENTS = (
    [parent(f"gi-0{i}", "multi_chunk", f"First part {i}. Second part {i}.") for i in range(1, 8)]
    + [parent(f"gi-1{i}", "single_fact", f"A single fact answer {i}.", keys=1) for i in range(1, 9)]
)


def built(seed: int = 7, parents=PARENTS, candidates=CANDIDATES):
    return build_synthetic(parents, candidates, seed=seed)


def of_kind(items, kind: str):
    return [s for s in items if s.kind == kind]


def test_ac_evl_07_calib_50_omission_keeps_the_first_sentence_of_a_qualifying_item() -> None:
    omissions = of_kind(built(), "omission")
    assert len(omissions) == 5
    for item in omissions:
        assert item.parent.output.category == "multi_chunk" and item.parent.key_points >= 2
        assert item.answer == item.parent.output.answer.split(". ")[0] + "."


def test_ac_evl_07_calib_51_items_that_do_not_qualify_for_omission_are_never_cut() -> None:
    parents = [parent("gi-01", "multi_chunk", "Only one sentence."),            # one sentence
               parent("gi-02", "multi_chunk", "One. Two.", keys=1),             # one key point
               parent("gi-03", "single_fact", "One. Two."),                      # not multi_chunk
               parent("gi-04", "multi_chunk", "Part one. Part two.")]
    omissions = of_kind(built(parents=parents), "omission")
    assert [o.parent.output.item_id for o in omissions] == ["gi-04"]  # fewer than 5 is allowed


def test_ac_evl_07_calib_52_an_insertion_is_a_concrete_sentence_of_another_drug() -> None:
    insertions = of_kind(built(), "insertion")
    assert len(insertions) == 5
    for item in insertions:
        original = item.parent.output.answer
        added = item.answer.removeprefix(original.rstrip()).strip()
        assert added.startswith(CONNECTOR) and "mg" in added
        source = next(c for c in CANDIDATES if c.doc_source == item.source_document)
        assert source.chunk_id not in item.parent.output.used_ids
        assert source.drug not in item.parent.drugs
        assert source.drug not in original.lower()


def test_ac_evl_07_calib_53_no_item_and_no_source_document_is_used_twice() -> None:
    items = built()
    parents = [s.parent.output.item_id for s in items]
    sources = [s.source_document for s in of_kind(items, "insertion")]
    assert len(items) == 10 and len(set(parents)) == 10 and len(set(sources)) == 5


def test_ac_evl_07_calib_54_a_chunk_in_the_packed_context_is_never_inserted() -> None:
    only = [candidate("ch-x", "betadrug", DOSE.format(n=9))]
    shown = [parent("gi-11", "single_fact", "Answer.", keys=1, used=("ch-x",))]
    assert of_kind(built(parents=shown, candidates=only), "insertion") == []


def test_ac_evl_07_calib_55_a_dash_in_the_text_keeps_an_output_out() -> None:
    dashed = [candidate("ch-x", "betadrug", "The usual adult dose is 5 mg — twice daily.")]
    plain = [parent("gi-11", "single_fact", "Answer.", keys=1)]
    assert built(parents=plain, candidates=dashed) == []
    assert built(parents=[parent("gi-12", "single_fact", "Answer – here.", keys=1)]) == []


def test_ac_evl_07_calib_56_the_same_seed_gives_the_same_set_another_seed_differs() -> None:
    assert built(seed=7) == built(seed=7)
    assert built(seed=7) != built(seed=8)


def test_ac_evl_07_calib_57_the_manifest_records_type_parent_hash_and_exact_text() -> None:
    manifest = manifest_synthetic(built(), seed=7, created=date(2026, 10, 14))
    assert manifest["counts"] == {"insertion": 5, "omission": 5}
    outputs = manifest["outputs"]
    assert [o["n"] for o in outputs] == list(range(1, 11))
    assert [o["synthetic_id"] for o in outputs] == [f"syn-{n:02d}" for n in range(1, 11)]
    first = outputs[0]
    original = next(p for p in PARENTS if p.output.item_id == first["parent_item_id"])
    assert first["parent_run_id"] == "run-1"
    assert first["parent_answer_hash"] == original.output.answer_hash
    assert first["answer_hash"] == answer_hash(first["answer"])
    assert first["perturbation"] in ("insertion", "omission")
    assert ("source_document" in first) == (first["perturbation"] == "insertion")


def test_ac_evl_07_calib_58_the_drug_name_comes_from_the_label_title() -> None:
    assert drug_of("Levothyroxine Sodium drug label") == "levothyroxine sodium"
    assert drug_of("Rubella") == "rubella"
