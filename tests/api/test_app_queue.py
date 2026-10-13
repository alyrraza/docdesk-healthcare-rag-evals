"""The API process must know the real broker, or enqueueing fails in production."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from docdesk.api.app import create_app
from docdesk.core.config import Settings
from docdesk.ingestion.tasks import ingest_document_task


def test_ac_ing_01_the_task_uses_the_broker_from_the_redis_setting(api_settings: Settings) -> None:
    """Tests inject a fake enqueue, so this is the only check that apply_async can reach Redis."""
    create_app(api_settings)
    assert ingest_document_task.app.conf.broker_url == api_settings.redis_url


def test_ac_ing_01_a_route_thread_sees_the_same_broker(api_settings: Settings) -> None:
    """Routes enqueue from threadpool threads, and Celery keeps its current app per thread."""
    create_app(api_settings)
    with ThreadPoolExecutor(max_workers=1) as pool:
        broker = pool.submit(lambda: ingest_document_task.app.conf.broker_url).result()
    assert broker == api_settings.redis_url
