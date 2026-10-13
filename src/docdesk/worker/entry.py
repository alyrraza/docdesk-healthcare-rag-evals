"""Worker entry point: `celery -A docdesk.worker.entry worker --pool=solo --loglevel=info`."""

from __future__ import annotations

from docdesk.core.config import get_settings
from docdesk.worker.celery_app import make_celery

celery_app = make_celery(get_settings().redis_url)
