# System design

Created 2026-10-13. Supersedes the v1 architecture (Stripe, Caddy). Read `MODULES.md` for the
module boundaries and `modules/*.md` for each module's detail.

## Principles
1. Modular monolith: one API app, one Celery worker, one eval CLI. Strict module boundaries,
   one public interface per module, files under 200 lines. See `DECISIONS.md` for why not microservices.
2. The model proposes, code disposes. Anything deterministic (disclaimer, score arithmetic, citation
   membership, SQL safety, budgets) is done in code, not by the model.
3. Measure first. Every request writes a trace, every change is judged by the eval harness.
4. Untrusted data stays data. Retrieved text and database rows never become instructions.
5. Fail safe. When unsure, abstain with a typed reason, never guess.

## Components
- FastAPI app: routers, auth middleware, error envelope, trace id per request.
- Celery worker: document ingestion, nightly eval runs.
- PostgreSQL with pgvector: users, documents, chunks and vectors, Synthea tables, prompt versions,
  traces, eval runs and results. Full text search is the keyword leg.
- Redis: token bucket, daily token budget, semantic cache, Celery broker.
- ONNX Runtime: embeddings and the optional reranker, CPU.
- LLM client: one interface, provider adapters behind it, retries, cost accounting.
- Eval CLI: loads the golden set, runs configurations, caches LLM calls, writes reports.
- Frontend: login, chat with citations, dashboard.

## Request flow (query)
1. Auth: verify the JWT, resolve the role.
2. Limits: token bucket, then the daily token budget (Redis).
3. Input guardrails: length limit, PII flag, injection heuristics, policy check (diagnosis, dose).
4. Cache: semantic lookup scoped to the user's documents and the active prompt bundle.
5. Router: `documents`, `structured` or `both`.
6. Documents path: dense top-N plus keyword top-N, reciprocal rank fusion, optional rerank to top-k.
7. Abstain check: best score under the threshold means abstain, no LLM call.
8. Structured path: generate SQL, validate (single SELECT, allowlist), run on a read-only role with a limit and timeout.
9. Context packer: fit evidence into the token budget, lowest ranked dropped first.
10. Generate with the active prompt bundle into the `AnswerOutput` schema.
11. Output guardrails: schema, citation membership, semantic checks, policy. One retry, then typed fallback.
12. Append the disclaimer in code. Write the trace row. Return the answer.

## Request flow (ingestion)
Upload returns 202 and a document id. The worker parses, cleans, chunks, embeds in batches, and
writes chunks in one transaction. Status moves `queued`, `processing`, `ready` or `failed`.
Identical content from the same user is detected by content hash and skipped.

## Data model (tables, key columns)
- `users`: id, email, password_hash, role, created_at
- `documents`: id, owner_id, title, source, content_hash, status, fail_reason, created_at
- `chunks`: id, document_id, position, text, token_count, embedding vector, tsv, chunker_version, embed_model_version
- `synthea_*`: patients, conditions, medications, encounters (read-only role access only)
- `prompt_versions`: id, name, version, content_hash, body, params, schema_version, status, created_at
- `active_prompts`: name, prompt_version_id, activated_by, activated_at (the pointer)
- `query_traces`: see `modules/observability.md` for the full field list
- `eval_runs`: id, config_id, prompt_bundle_id, split, started_at, git_sha
- `eval_results`: run_id, item_id, metrics json, failure_label, trace json

## Failure and degradation
| Dependency down | Behavior |
|---|---|
| Redis | cache bypassed (open); budget check fails closed with 503 so cost cannot run away |
| LLM provider | one retry with backoff, then typed fallback `system_error`; trace records it |
| Database | 503 with the standard envelope; no partial writes |
| Reranker error | skip rerank, record it in the trace, continue with fused order |
| Embedding model missing | worker fails the job with a clear reason; API stays up |

## Security model
JWT with short lifetime and role claim. Passwords hashed with a slow salted hash. Admin routes
require the role. SQL runs only through the validator on a read-only role. Documents are scoped
per user at the retrieval layer. Secrets only from environment variables. Rate limit and daily
budget protect the free LLM tier. Retrieved text is delimited and treated as untrusted.

## Deployment
Dockerfiles for the API and worker and a compose file (api, worker, postgres with pgvector,
redis, optional prometheus and grafana). Not run locally. GitHub Actions builds the images.
A hosted deployment is parked until budget allows.
