# Tech stack

Created 2026-10-13. Only things listed here may be used. To add one, add it here in the same
commit with the reason. Pin exact versions at install time (`pip freeze` into a lock file) and
record them in the README. Versions are not guessed in this document.

## Backend
| Need | Choice | Why |
|---|---|---|
| API | FastAPI + Uvicorn | async, typed, automatic OpenAPI |
| Validation and settings | Pydantic v2, pydantic-settings | one schema layer for API, LLM output and config |
| Database access | SQLAlchemy 2.x + Alembic + psycopg | explicit sessions, real migrations |
| Vector search | pgvector extension | vectors and relational data in one database |
| Keyword search | Postgres full text search | second retrieval leg without a new service |
| Queue and cache | Redis (Memurai on Windows dev) | broker, rate limiter, semantic cache |
| Background jobs | Celery | async ingestion and nightly evals |
| Auth | PyJWT + passlib or argon2-cffi | standard, small |
| HTTP client | httpx | async, timeouts by default |
| Metrics | prometheus-client | `/metrics` endpoint |
| Logging | stdlib logging with a JSON formatter | no extra dependency |

## ML
| Need | Choice | Why |
|---|---|---|
| Embeddings | a small sentence embedding model, pre-exported ONNX, run with onnxruntime | CPU only, no PyTorch |
| Tokenizer | `tokenizers` | token counting for budgets and chunking |
| Reranker | a small cross-encoder, ONNX | optional stage, measured in the matrix |
| LLM generator and judge | two different providers or models behind `llm/client.py` | judge must differ from generator; choose after checking current free tiers |

## Evaluation (built in-house)
The harness, metrics and judge are written by hand so each one can be explained in an
interview. No RAGAS or DeepEval dependency. Optional: cross-check one metric against RAGAS once
and report the agreement in the README.
Extra libraries allowed: numpy (bootstrap), scikit-learn (`cohen_kappa_score` only), matplotlib (plots).

## Frontend
React + TypeScript + Vite, a small CSS approach (plain CSS modules), no UI framework needed.
Charts for the dashboard: one small chart library chosen at task T146.

## Quality tooling
pytest, pytest-asyncio, ruff, mypy, pre-commit style hooks via `.githooks`.

## Packaging and CI
Dockerfile (API and worker), `docker-compose.yml` (api, worker, postgres+pgvector, redis; optional
grafana and prometheus), GitHub Actions: lint, test, retrieval-only eval gate, Docker image build.
None of the Docker pieces are run locally.

## Data
openFDA drug labels, MedlinePlus health topics, a few open-access papers and public guidelines
(about 200 to 400 documents), and Synthea synthetic patients for the structured tables.
No MIMIC and no real patient data.
