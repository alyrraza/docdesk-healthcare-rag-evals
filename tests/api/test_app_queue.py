"""The API process must know the real broker, or enqueueing fails in production."""

from __future__ import annotations

from docdesk.api.app import create_app
from docdesk.core.config import Settings
from docdesk.ingestion.tasks import ingest_document_task


def test_ac_ing_01_the_task_uses_the_broker_from_the_redis_setting(api_settings: Settings) -> None:
    """Tests inject a fake enqueue, so this is the only check that apply_async can reach Redis."""
    create_app(api_settings)
    assert ingest_document_task.app.conf.broker_url == api_settings.redis_url
