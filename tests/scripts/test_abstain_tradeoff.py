"""T102a (AC-GEN-03): the abstain threshold trade-off table is computed by code from B0 rows."""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from abstain_tradeoff import Probe, build_report, sweep_row, thresholds  # noqa: E402
from abstain_tradeoff_render import render_markdown  # noqa: E402
from docdesk.query.service import ABSTAIN_POLICY  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]

PROBES = [
    Probe("a1", "answerable", 0.60, "answered"),
    Probe("a2", "answerable", 0.52, "abstained"),
    Probe("a3", "answerable", 0.70, "answered"),
    Probe("u1", "unanswerable", 0.45, "abstained"),
    Probe("u2", "unanswerable", 0.62, "abstained"),
    Probe("x1", "adversarial", 0.50, "refused"),
    Probe("x2", "adversarial", 0.48, "abstained"),
]


def test_ac_gen_03_grid_runs_from_040_to_070_in_steps_of_001() -> None:
    grid = thresholds()
    assert grid[0] == 0.40 and grid[-1] == 0.70 and len(grid) == 31
    assert all(round(b - a, 2) == 0.01 for a, b in zip(grid, grid[1:], strict=False))


def test_ac_gen_03_nothing_abstains_at_a_threshold_below_every_score() -> None:
    row = sweep_row(PROBES, 0.40)
    assert (row["answerable_wrongly_abstained"], row["unanswerable_abstained"]) == (0, 0)
    assert row["generator_calls_saved"] == 0


def test_ac_gen_03_a_score_equal_to_the_threshold_is_not_abstained() -> None:
    row = sweep_row(PROBES, 0.50)  # x1 scores exactly 0.50
    assert row["unanswerable_abstained"] == 1
    assert row["generator_calls_saved"] == 2  # u1 and x2


def test_ac_gen_03_wrong_abstain_counts_answerable_items_and_marks_lost_answers() -> None:
    row = sweep_row(PROBES, 0.55)
    assert row["answerable_wrongly_abstained"] == 1  # a2
    assert row["answerable_lost_answers"] == 0  # B0 had already abstained on a2
    row = sweep_row(PROBES, 0.65)
    assert row["answerable_wrongly_abstained"] == 2  # a1 and a2
    assert row["answerable_lost_answers"] == 1  # B0 had answered a1


def test_ac_gen_03_calls_saved_skip_items_refused_before_the_generator() -> None:
    row = sweep_row(PROBES, 0.65)
    assert row["unanswerable_abstained"] == 2
    assert row["generator_calls_saved"] == 5  # a1 a2 u1 u2 x2, not x1 (refused by policy)


def test_ac_gen_03_report_states_the_facts_from_the_rows() -> None:
    facts = build_report(PROBES)["facts"]
    assert facts["unanswerable_generator_abstained"] == [2, 2]
    assert facts["answerable_top1_min"] == 0.52
    assert facts["unanswerable_top1_max"] == 0.62
    assert facts["ranges_overlap"] is True


def test_ac_gen_03_markdown_names_the_decision_and_every_number_it_quotes() -> None:
    text = render_markdown(build_report(PROBES))
    assert "2 of 2" in text and "0.520" in text and "0.620" in text
    assert "stays 0.0" in text and "not tuned into B0" in text and "Phase 5" in text
    assert "\u2014" not in text and "\u2013" not in text
    assert text.count("| 0.") >= 31


def test_ac_gen_03_report_is_plain_json_data() -> None:
    assert json.loads(json.dumps(build_report(PROBES)))["config"] == "b0"


def test_ac_gen_03_b0_and_the_live_policy_keep_threshold_zero() -> None:
    config = tomllib.loads((ROOT / "evals" / "configs" / "b0.toml").read_text(encoding="utf-8"))
    assert config["abstain"]["threshold"] == 0.0
    assert ABSTAIN_POLICY.default == 0.0 and ABSTAIN_POLICY.thresholds == {}
