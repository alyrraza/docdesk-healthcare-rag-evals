"""Dependencies that tests replace: where files go and how a job reaches the worker."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from pathlib import Path

from fastapi import Depends

from docdesk.core.config import Settings, get_settings
from docdesk.ingestion.filestore import LocalFileStore

Enqueue = Callable[[uuid.UUID], None]


def get_file_store(settings: Settings = Depends(get_settings)) -> LocalFileStore:
    """Give routes the upload folder from settings, so tests can swap in a fake."""
    return LocalFileStore(Path(settings.upload_dir))


def send_to_worker(document_id: uuid.UUID) -> None:
    """Queue one ingestion job; imported here so the API does not load the model code."""
    from docdesk.ingestion.tasks import ingest_document_task

    ingest_document_task.apply_async(args=[str(document_id)], retry=False)


def get_enqueue() -> Enqueue:
    """Give routes the queue function, so tests can record jobs without a Redis."""
    return send_to_worker
