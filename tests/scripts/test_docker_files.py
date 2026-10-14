"""AC-DEP-03: the Dockerfile, .dockerignore and compose file keep the deployment promises.

Docker is not installed on the author's laptop, so these tests read the files. The real build
and the compose smoke run in the image-build CI job.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = (ROOT / "Dockerfile").read_text(encoding="utf-8")
IGNORE = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
COMPOSE_TEXT = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
COMPOSE: dict[str, Any] = yaml.safe_load(COMPOSE_TEXT)


def test_ac_dep_03_base_images_are_pinned_to_a_full_tag() -> None:
    images = re.findall(r"^FROM (\S+)", DOCKERFILE, re.MULTILINE)
    assert len(images) >= 3, "expected a multi stage build"
    for image in images:
        assert re.search(r":\d+\.\d+\.\d+", image), image
    for service in COMPOSE["services"].values():
        image = service.get("image", "")
        assert ":latest" not in image and (image == "" or ":" in image), image


def test_ac_dep_03_image_runs_as_a_non_root_user_with_a_health_check() -> None:
    users = re.findall(r"^USER (\S+)", DOCKERFILE, re.MULTILINE)
    assert users and users[-1] not in ("root", "0")
    assert "HEALTHCHECK" in DOCKERFILE and "/health" in DOCKERFILE


def test_ac_dep_03_image_has_no_dev_dependencies_and_no_secret_files() -> None:
    assert "[dev]" not in DOCKERFILE
    for line in DOCKERFILE.splitlines():
        if line.startswith(("COPY", "ADD")):
            assert ".env" not in line.replace(".env.example", ""), line
    assert not re.search(r"^(ENV|ARG) .*(SECRET|PASSWORD|API_KEY)", DOCKERFILE, re.MULTILINE)


def test_ac_dep_03_model_comes_from_the_checked_fetch_script() -> None:
    assert "fetch_model.py" in DOCKERFILE and "COPY --from=model" in DOCKERFILE


def test_ac_dep_03_dockerignore_keeps_secrets_data_and_notes_out_of_the_context() -> None:
    for entry in (".env", ".git", "data", ".cache", "evals/cache", "PROJECT_NOTES.md", "docs"):
        assert entry in IGNORE, entry


def test_ac_dep_03_compose_has_four_services_with_health_checks_and_named_volumes() -> None:
    services = COMPOSE["services"]
    assert set(services) == {"db", "redis", "api", "worker"}
    assert services["db"]["image"] == "pgvector/pgvector:pg16"
    for name in ("db", "redis", "worker"):
        assert "healthcheck" in services[name], name
    assert set(COMPOSE["volumes"]) >= {"pgdata", "redisdata", "uploads"}


def test_ac_dep_03_only_the_api_runs_migrations_and_the_worker_waits_for_it() -> None:
    services = COMPOSE["services"]
    assert services["api"]["environment"]["RUN_MIGRATIONS"] == "1"
    assert "RUN_MIGRATIONS" not in services["worker"]["environment"]
    assert services["worker"]["depends_on"]["api"]["condition"] == "service_healthy"


def test_ac_dep_03_compose_holds_no_literal_secret() -> None:
    for line in COMPOSE_TEXT.splitlines():
        if re.search(r"(PASSWORD|SECRET|API_KEY)\s*:", line):
            assert "${" in line, line
    assert not re.search(r"://[^:@\s]+:(?!\$)[^@\s]+@", COMPOSE_TEXT)


def test_ac_dep_03_deployment_files_have_no_em_or_en_dash() -> None:
    for name in ("Dockerfile", "docker-compose.yml", ".dockerignore", "Makefile",
                 "docker/entrypoint.sh", ".env.example"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "\u2014" not in text and "\u2013" not in text, name


def test_ac_dep_03_entrypoint_migrates_only_when_asked_then_hands_over() -> None:
    script = (ROOT / "docker" / "entrypoint.sh").read_text(encoding="utf-8")
    assert "alembic upgrade head" in script and 'exec "$@"' in script
    assert "RUN_MIGRATIONS" in script
