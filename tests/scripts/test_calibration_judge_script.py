"""T100 (AC-EVL-07): the script judges the synthetic outputs, spending nothing before a check."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from calibration_judge import RESULTS, Wiring, main  # noqa: E402
from calibration_synthetic import SynthSource  # noqa: E402
from docdesk.evals.budget import BudgetStop  # noqa: E402
from docdesk.evals.cache import CachedClient  # noqa: E402
from docdesk.evals.calib_judge import context_text  # noqa: E402
from docdesk.evals.calib_sample import answer_hash  # noqa: E402
from docdesk.evals.calib_sheet import ChunkView  # noqa: E402
from docdesk.evals.judges.faithfulness import judge_faithfulness  # noqa: E402
from docdesk.evals.judges.kit import load_judge_kit  # noqa: E402
from docdesk.evals.judges.parser import JudgeParser  # noqa: E402
from docdesk.evals.judges.schemas import FaithfulnessJudgement  # noqa: E402
from docdesk.evals.report_data import ResultRecord  # noqa: E402
from fakes.llm import FakeLLMClient  # noqa: E402

PARENT = "Tablets are 25 mg."
SYNTHETIC = "Tablets are 25 mg. In addition, the dose is 900 mg."
CHUNKS = [ChunkView("Label", "Tablets 25 mg.")]
FAITH = json.dumps({"claims": [{"claim": "25 mg", "label": "supported"}]})
CORRECT = json.dumps({"key_points": [{"point": 1, "label": "covered"}]})
PROMPTS = Path("prompts")
MODEL = "judge-x"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    golden = [{"id": "gi-001", "type": "single_fact", "split": "dev", "question": "Strengths?",
               "answerable": True, "gold_route": "documents",
               "gold_facts": ["Tablets come in 25 mg"],
               "gold_evidence": [{"source": "seed:openfda:a", "text": "25 mg"}]}]
    folder = tmp_path / "evals" / "golden"
    folder.mkdir(parents=True)
    (folder / "batch.yaml").write_text(yaml.safe_dump(golden, sort_keys=False), encoding="utf-8")
    manifest = {"outputs": [{
        "n": 1, "synthetic_id": "syn-01", "parent_item_id": "gi-001", "parent_run_id": "run-1",
        "parent_answer_hash": answer_hash(PARENT), "answer": SYNTHETIC,
        "answer_hash": answer_hash(SYNTHETIC), "key_points": 1}]}
    calibration = tmp_path / "evals" / "calibration"
    calibration.mkdir(parents=True)
    (calibration / "manifest_synthetic.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    return tmp_path


def source(meta: dict | None = None) -> SynthSource:
    trace = {"answer": PARENT, "used_ids": ["ch-a"], "judge_model": MODEL,
             "judge_prompts": load_judge_kit(PROMPTS, FakeLLMClient([]), MODEL).prompt_hashes()}
    trace.update(meta or {})
    metrics = {"status": "ok", "type": "single_fact", "outcome": "answered"}
    rows = [ResultRecord("gi-001", metrics, None, trace)]
    return SynthSource(runs=lambda ids: [("run-1", rows)], chunks=lambda ids: list(CHUNKS),
                       candidates=lambda: [])


def prime_cache(cache: Path) -> None:
    """Store the judge call the original run made for the parent answer, as a real run would."""
    kit = load_judge_kit(PROMPTS, CachedClient(FakeLLMClient([FAITH]), cache), MODEL)
    judge_faithfulness(
        prompt=kit.faithfulness_prompt, parser=JudgeParser(FaithfulnessJudgement),
        client=kit.client, model=MODEL, question="Strengths?", answer=PARENT,
        evidence=context_text(CHUNKS), answered=True)


def go(project: Path, tmp_path: Path, args: list[str], client: FakeLLMClient, **wiring) -> int:
    live = CachedClient(client, tmp_path / "cache")
    return main(args, project_root=project, wiring=Wiring(
        source=wiring.pop("src", source()), live_client=lambda: live, judge_model=MODEL,
        prompts_dir=PROMPTS, cache_dir=tmp_path / "cache"))


def test_ac_evl_07_judgescript_01_check_passes_only_when_the_parent_call_is_in_the_cache(
    project: Path, tmp_path: Path, capsys
) -> None:
    client = FakeLLMClient([])
    assert go(project, tmp_path, ["--check"], client) == 1
    assert "gi-001" in capsys.readouterr().out and client.requests == []
    prime_cache(tmp_path / "cache")
    assert go(project, tmp_path, ["--check"], client) == 0
    assert client.requests == []  # the check never reaches a model


def test_ac_evl_07_judgescript_02_run_refuses_to_spend_when_the_check_fails(
    project: Path, tmp_path: Path
) -> None:
    client = FakeLLMClient([FAITH, CORRECT])
    with pytest.raises(SystemExit, match="context"):
        go(project, tmp_path, ["--run"], client)
    assert client.requests == [] and not (project / RESULTS).exists()


def test_ac_evl_07_judgescript_03_run_writes_the_results_and_never_overwrites(
    project: Path, tmp_path: Path, capsys
) -> None:
    prime_cache(tmp_path / "cache")
    client = FakeLLMClient([FAITH, CORRECT])
    assert go(project, tmp_path, ["--run"], client) == 0
    saved = yaml.safe_load((project / RESULTS).read_text(encoding="utf-8"))
    assert saved["judge_model"] == MODEL and saved["results"][0]["synthetic_id"] == "syn-01"
    assert "tokens" in capsys.readouterr().out
    with pytest.raises(SystemExit, match="already exists"):
        go(project, tmp_path, ["--run"], FakeLLMClient([]))


def test_ac_evl_07_judgescript_04_a_judge_that_differs_from_the_original_run_stops_it(
    project: Path, tmp_path: Path
) -> None:
    prime_cache(tmp_path / "cache")
    with pytest.raises(SystemExit, match="judge_model"):
        go(project, tmp_path, ["--run"], FakeLLMClient([]), src=source({"judge_model": "other"}))
    with pytest.raises(SystemExit, match="judge_prompts"):
        go(project, tmp_path, ["--run"], FakeLLMClient([]), src=source({"judge_prompts": {}}))


def test_ac_evl_07_judgescript_05_a_budget_stop_exits_2_and_writes_nothing(
    project: Path, tmp_path: Path, capsys
) -> None:
    prime_cache(tmp_path / "cache")
    assert go(project, tmp_path, ["--run"], FakeLLMClient([BudgetStop("daily limit reached")])) == 2
    assert "daily limit reached" in capsys.readouterr().out
    assert not (project / RESULTS).exists()
