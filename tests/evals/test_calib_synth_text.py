"""T099 (AC-EVL-07): the text edits that make synthetic calibration outputs are fixed rules."""

from __future__ import annotations

from docdesk.evals.calib_synth_text import (
    CONNECTOR,
    add_insertion,
    insertion_sentences,
    keep_first_sentence,
    split_sentences,
)


def test_ac_evl_07_calib_40_sentences_are_split_at_full_stops_and_line_breaks() -> None:
    text = "It is rare. It can be severe!\n- Call a doctor"
    assert split_sentences(text) == ["It is rare.", "It can be severe!", "- Call a doctor"]
    assert split_sentences("Tardive dyskinesia") == ["Tardive dyskinesia"]


def test_ac_evl_07_calib_41_a_decimal_or_an_abbreviation_does_not_split_a_sentence() -> None:
    assert len(split_sentences("The dose is 0.5 mg daily, e.g. in the morning. Take it.")) == 2


def test_ac_evl_07_calib_42_omission_keeps_only_the_first_sentence() -> None:
    assert keep_first_sentence("First part. Second part. Third.") == "First part."


def test_ac_evl_07_calib_43_a_connector_joins_the_sentence_as_part_of_the_answer() -> None:
    joined = add_insertion("The label warns of sedation.", "The usual dose is 5 mg twice daily.")
    assert joined == f"The label warns of sedation. {CONNECTOR}the usual dose is 5 mg twice daily."
    # An answer with no final stop gets one first.
    assert add_insertion("Tardive dyskinesia", "The usual dose is 5 mg.").startswith(
        f"Tardive dyskinesia. {CONNECTOR}")


def test_ac_evl_07_calib_44_only_concrete_self_contained_sentences_are_candidates() -> None:
    chunk = (
        "The usual adult dose is 5 mg twice daily. "          # number and dose: keep
        "Patients should be monitored every 3 months. "      # schedule: keep
        "Store in a cool place. "                            # no concrete claim: drop
        "The drug is a tablet that is white. "               # no concrete claim: drop
        "Doses above 40 mg are not recommended (see DOSAGE). "  # cross reference: drop
        "Metformin may cause lactic acidosis at 2 g. "       # names the drug: drop
        "It can be given with food, 10 mg."                  # starts with a pronoun: drop
    )
    found = insertion_sentences(chunk, drug="metformin")
    assert found == ["The usual adult dose is 5 mg twice daily.",
                     "Patients should be monitored every 3 months."]


def test_ac_evl_07_calib_45_headings_and_dangling_references_are_not_candidates() -> None:
    chunk = (
        "Dosage and administration 2 DOSAGE AND ADMINISTRATION Recommended dose is 1 mg daily. "
        "The risk did not vary by age (5 to 100 years) in the trials analyzed. "
        "The study found that 20 mg was too high. "
        "Treatment is given for 7 to 14 days in total. "
        "The usual range is 2 to 6 mg/day in divided doses."
    )
    assert insertion_sentences(chunk, drug="metformin") == [
        "The usual range is 2 to 6 mg/day in divided doses."]


def test_ac_evl_07_calib_46_fragments_and_table_text_are_not_candidates() -> None:
    glued = "The tablets hold 4.5 mg of base. structural formula"            # heading glued on
    no_stop = "The older adults will need 100 mg b.i.d.(twice daily)"       # no final stop
    symbol = "The dose for ages 1 Month to < 6 Months is 14 mg/kg daily."   # table symbol
    fine = "The adult dose is 5 mg twice daily."
    for text in (glued, no_stop, symbol):
        assert insertion_sentences(text, drug="metformin") == []
    assert insertion_sentences(fine, drug="metformin") == [fine]


def test_ac_evl_07_calib_47_broken_brackets_and_title_case_runs_are_not_candidates() -> None:
    broken = "The dose in adults is greater than or equal to 50 mL/minute (2.1."
    title_case = "The 5 mg tablets also contain FD&C Yellow No. 6 Aluminum Lake."
    headings = "The dose in Adult and Pediatric Patients with Renal Impairment is 5 mg."
    names = "The usual dose in Parkinson disease is 5 mg twice daily."  # one proper name is fine
    for text in (broken, title_case, headings):
        assert insertion_sentences(text, drug="metformin") == []
    assert insertion_sentences(names, drug="metformin") == [names]
