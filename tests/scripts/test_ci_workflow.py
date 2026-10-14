"""T101 (AC-EVL-06): the workflow file parses, its commands exist and it holds no secret.

GitHub Actions cannot run here, so these tests check the file itself, not a real run.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def workflow() -> dict[str, Any]:
    """The parsed workflow; the YAML key `on` is read by PyYAML as the boolean True."""
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def run_lines(job: dict[str, Any]) -> list[str]:
    """Every shell line of every `run` step of one job, in order."""
    lines: list[str] = []
    for step in job["steps"]:
        lines += [line.strip() for line in step.get("run", "").splitlines() if line.strip()]
    return lines


def test_ac_evl_06_workflow_runs_on_push_to_main_and_on_pull_requests() -> None:
    triggers = workflow()[True]
    assert triggers["push"]["branches"] == ["main"]
    assert "pull_request" in triggers


def test_ac_evl_06_workflow_has_a_test_job_and_a_retrieval_gate_job() -> None:
    assert set(workflow()["jobs"]) >= {"test", "retrieval-gate"}


def test_ac_evl_06_every_job_uses_a_pgvector_postgres_service() -> None:
    for name, job in workflow()["jobs"].items():
        assert "pgvector" in job["services"]["postgres"]["image"], name


def test_ac_evl_06_every_python_script_the_workflow_runs_exists() -> None:
    for job in workflow()["jobs"].values():
        for line in run_lines(job):
            for script in re.findall(r"python (scripts/\S+\.py)", line):
                assert (ROOT / script).is_file(), script


def test_ac_evl_06_every_python_module_the_workflow_runs_is_installed() -> None:
    for job in workflow()["jobs"].values():
        for line in run_lines(job):
            for module in re.findall(r"python -m (\w+)", line):
                assert importlib.util.find_spec(module), module


def test_ac_evl_06_test_job_runs_lint_checks_and_the_suite() -> None:
    lines = " | ".join(run_lines(workflow()["jobs"]["test"]))
    for command in ("python -m ruff check .", "python -m pytest", "scripts/check_file_length.py",
                    "scripts/check_docs_style.py", "scripts/fetch_model.py"):
        assert command in lines, command


def test_ac_evl_06_gate_job_loads_the_model_migrates_then_runs_the_gate() -> None:
    lines = run_lines(workflow()["jobs"]["retrieval-gate"])
    order = [next(i for i, line in enumerate(lines) if key in line)
             for key in ("scripts/fetch_model.py", "alembic upgrade head", "scripts/ci_gate.py")]
    assert order == sorted(order)
    assert "--write-baseline" not in " ".join(lines)


def test_ac_evl_06_gate_job_needs_no_provider_key() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "secrets." not in text
    for word in ("GROQ", "OPENROUTER", "gsk_", "neon", "sk-"):
        assert word.lower() not in text.lower(), word


def test_ac_evl_06_database_urls_hold_no_literal_password() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    # A password may only be a shell variable filled in at run time, never a typed value.
    assert not re.search(r"postgres(?:ql)?(?:\+\w+)?://[^:@\s]+:(?!\$)[^@\s]+@", text)


def test_ac_evl_06_workflow_actions_are_pinned_to_a_version() -> None:
    for job in workflow()["jobs"].values():
        for step in job["steps"]:
            if "uses" in step:
                assert re.search(r"@v\d+$", step["uses"]), step["uses"]


def test_ac_evl_06_workflow_text_has_no_em_or_en_dash() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "\u2014" not in text and "\u2013" not in text


def test_ci_runner_is_pinned_and_actions_are_node_24_majors() -> None:
    """F11: no floating runner image, and no Node 20 action majors."""
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "ubuntu-latest" not in text and "ubuntu-24.04" in text
    assert "actions/checkout@v4" not in text and "actions/setup-python@v5" not in text
