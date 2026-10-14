# Module: backend (core, db, auth, api)

Created 2026-10-13. Criteria: AC-AUTH-01 to 05, AC-ING-01 (upload route), AC-PRM-02 (admin route).

## core
- `config.py`: `Settings` (pydantic-settings). Reads environment variables only. Fields: database url,
  redis url, JWT secret and lifetime, LLM keys, token budgets, file paths. Fails at startup if a required value is missing.
- `errors.py`: `AppError(code, message, status)` and one handler that renders the standard envelope with the trace id.
- `logging.py`: JSON log formatter. Every log line carries `trace_id` from a context variable.
- `ids.py`: `new_trace_id()`. `clock.py`: `utc_now()` so tests can freeze time.

## db
- `session.py`: engine and a per-request session dependency that always closes.
- `models/`: one file per table group (users, documents, chunks, prompts, traces, evals).
- `repositories/`: one class per table. Methods take and return plain dataclasses. All queries parameterized.
- Migrations: Alembic only. pgvector extension is enabled in its own migration. Vector index choice
  (HNSW or IVFFlat) is recorded in `DECISIONS.md` with the reason.
- A second, read-only database role exists for the SQL branch (`docdesk_readonly`), granted SELECT only on the Synthea tables.

## auth
- `passwords.py`: `hash_password`, `verify_password`. Slow salted hash. Never log or return a password.
- `jwt.py`: `create_token(user)`, `decode_token(token)`. Claims: `sub`, `role`, `exp`. Short lifetime.
- `deps.py`: `require_user`, `require_admin` FastAPI dependencies. Missing or bad token gives 401, wrong role gives 403.
- `roles.py`: the `Role` enum (`user`, `admin`).
Security-sensitive: after writing, explain each function line by line to Ali.

## api
- `app.py`: `create_app()` wires routers, error handler, CORS (explicit origins), metrics route.
- `public.py`: `PUBLIC_ROUTES` allowlist (`/health`, `/`, `/static/{name}`, `/auth/register`, `/auth/login`, `/metrics` if protected otherwise).
- `routers/`: `auth.py`, `documents.py`, `query.py`, `prompts_admin.py`, `traces.py`, `health.py`. One file each.
- `schemas/`: request and response models, one file per router.
- Routers are thin: validate, call one service function, shape the response.

## Endpoints
| Method and path | Auth | Purpose |
|---|---|---|
| POST `/auth/register` | public | create user (AC-AUTH-01) |
| POST `/auth/login` | public | return JWT (AC-AUTH-02) |
| GET `/health` | public | liveness |
| GET `/` and `/static/{name}` | public | the web page and its six fixed files, see `docdesk/web/` |
| POST `/documents` | user | upload, returns 202 (AC-ING-01) |
| GET `/documents` and `/documents/{id}` | user | list and status |
| POST `/query` | user | ask a question; `data` has answer, disclaimer, abstained, abstain_reason, citations |
| POST `/retrieve` | user | the ranked chunks with title and score, no model call (used by the web page) |
| GET `/traces` and `/traces/{id}` | user (own), admin (all) | trace inspection |
| GET `/admin/prompts`, POST `/admin/prompts/{name}/activate` | admin | prompt versions and pointer (AC-PRM-02) |
| GET `/admin/eval/runs` | admin | eval dashboard data |

## Tests
Per endpoint: success, auth failure, bad input. Plus the public route allowlist test (AC-AUTH-05)
that walks the OpenAPI routes. Integration tests use a real Postgres.
