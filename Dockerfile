# Production image for the API and the Celery worker. Build: docker build -t docdesk .
# Three stages: fetch the pinned model, install the runtime dependencies, then copy both into a
# slim image that runs as a normal user. No dev dependencies and no secrets end up in a layer.

FROM python:3.11.13-slim-bookworm AS model
RUN pip install --no-cache-dir "httpx>=0.27,<1"
COPY scripts/fetch_model.py /fetch_model.py
# Downloads the pinned revision and stops the build if a sha256 differs from the pin.
RUN python /fetch_model.py --dest /models/all-MiniLM-L6-v2

FROM python:3.11.13-slim-bookworm AS build
WORKDIR /build
COPY pyproject.toml ./
COPY src ./src
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir . \
    && /opt/venv/bin/pip uninstall -y docdesk

FROM python:3.11.13-slim-bookworm AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/opt/venv/bin:$PATH \
    PYTHONPATH=/app/src \
    MODEL_DIR=/opt/models/all-MiniLM-L6-v2 \
    UPLOAD_DIR=/app/data/uploads \
    OPENBLAS_NUM_THREADS=1
RUN useradd --system --uid 10001 --create-home docdesk \
    && mkdir -p /app/data/uploads \
    && chown -R docdesk:docdesk /app/data
WORKDIR /app
COPY --from=build /opt/venv /opt/venv
COPY --from=model /models /opt/models
COPY alembic.ini ./
COPY migrations ./migrations
COPY prompts ./prompts
COPY scripts ./scripts
COPY evals/configs/b0.toml ./evals/configs/b0.toml
COPY evals/ci ./evals/ci
COPY src ./src
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 0755 /usr/local/bin/entrypoint.sh
USER docdesk
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"
ENTRYPOINT ["entrypoint.sh"]
CMD ["uvicorn", "docdesk.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
