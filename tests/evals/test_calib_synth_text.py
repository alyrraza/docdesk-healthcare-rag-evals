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
