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


def test_ac_evl_06_every_python_job_uses_a_pgvector_postgres_service() -> None:
    """The image-build job gets its database from docker-compose.yml (test_docker_files)."""
    for name, job in workflow()["jobs"].items():
        if name != "image-build":
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


def image_build() -> dict[str, Any]:
    """The image-build job, which builds the Dockerfile and starts the compose stack."""
    return workflow()["jobs"]["image-build"]


def test_ac_dep_04_image_build_runs_the_compose_smoke_in_order() -> None:
    lines = run_lines(image_build())
    order = [next(i for i, line in enumerate(lines) if key in line)
             for key in ("make_env.py", "docker compose up", "demo_seed.py", "demo_retrieve.py")]
    assert order == sorted(order)
    assert "--expect seed:medlineplus:medlineplus-387" in " ".join(lines)


def test_ac_dep_04_image_build_never_calls_the_model() -> None:
    text = " ".join(run_lines(image_build()))
    for word in ("smoke_llm", "evals.cli", "GROQ", "/query"):
        assert word not in text, word


def test_ac_dep_04_only_the_image_build_job_may_write_packages() -> None:
    jobs = workflow()["jobs"]
    assert workflow()["permissions"] == {"contents": "read"}
    assert image_build()["permissions"] == {"contents": "read", "packages": "write"}
    assert [n for n, j in jobs.items() if "permissions" in j] == ["image-build"]


def test_ac_dep_04_push_runs_on_main_pushes_only_and_after_the_smoke() -> None:
    steps = image_build()["steps"]
    pushes = [i for i, s in enumerate(steps) if "docker push" in s.get("run", "")]
    assert pushes, "no push step"
    for index in pushes:
        condition = steps[index].get("if", "")
        assert "github.event_name == 'push'" in condition and "refs/heads/main" in condition
    smoke = next(i for i, s in enumerate(steps) if "demo_retrieve.py" in s.get("run", ""))
    login = next(i for i, s in enumerate(steps) if "docker login" in s.get("run", ""))
    assert smoke < login < min(pushes)


def test_ac_dep_04_push_uses_the_workflow_token_and_tags_sha_and_latest() -> None:
    text = " ".join(s.get("run", "") for s in image_build()["steps"])
    assert "--password-stdin" in text and "ghcr.io/${GITHUB_REPOSITORY,,}" in text
    assert "$GITHUB_SHA" in text and ":latest" in text
