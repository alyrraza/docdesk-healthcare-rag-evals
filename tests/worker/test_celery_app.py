"""The Celery app takes its broker from settings and runs safely on Windows (AC-ING-01)."""

from __future__ import annotations

import sys

import pytest

from docdesk.worker.celery_app import make_celery

URL = "redis://127.0.0.1:6380/0"


def test_ac_ing_01_the_broker_and_result_url_come_from_the_argument() -> None:
    app = make_celery(URL)
    assert app.conf.broker_url == URL
    assert app.conf.result_backend == URL


def test_ac_ing_03_a_job_is_acknowledged_only_after_it_finishes() -> None:
    """So a worker killed mid-job leaves the job in the queue to be retried."""
    app = make_celery(URL)
    assert app.conf.task_acks_late is True
    assert app.conf.task_reject_on_worker_lost is True


def test_ac_ing_03_the_ingestion_tasks_module_is_loaded_by_the_worker() -> None:
    assert "docdesk.ingestion.tasks" in make_celery(URL).conf.include


def test_ac_ing_01_windows_uses_the_solo_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    assert make_celery(URL).conf.worker_pool == "solo"


def test_ac_ing_01_other_systems_keep_the_default_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    assert make_celery(URL).conf.worker_pool == "prefork"
