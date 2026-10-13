"""Celery app factory. The broker address always comes from settings, never from code."""

from __future__ import annotations

import sys

from celery import Celery


def make_celery(redis_url: str) -> Celery:
    """Build the app in a function so tests can create one without a running Redis."""
    app = Celery(
        "docdesk",
        broker=redis_url,
        backend=redis_url,
        include=["docdesk.ingestion.tasks"],
    )
    app.conf.update(
        # Acknowledge after the job ends, so a worker killed mid-job leaves it queued to retry.
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
        # The default prefork pool does not work on Windows; solo runs one job at a time.
        worker_pool="solo" if sys.platform == "win32" else "prefork",
    )
    return app
