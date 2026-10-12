# Modules

Created 2026-10-13. Every module is a folder under `src/docdesk/` with one public interface
(exported from `__init__.py`). Other modules import only that interface. Each file stays under
200 lines and has one responsibility. A dependency not listed here is a design change.

| Module | Responsibility | Public interface | May depend on |
|---|---|---|---|
| `core` | settings, error envelope, logging, ids, clock | `Settings`, `AppError`, `get_logger`, `new_trace_id` | nothing |
| `db` | engine, sessions, models, repositories | `get_session`, repositories per table | `core` |
| `auth` | passwords, JWT, roles, request dependencies | `hash_password`, `verify_password`, `create_token`, `require_user`, `require_admin` | `core`, `db` |
| `api` | routers, schemas, app factory | `create_app` | all services below through their interfaces |
| `ingestion` | parse, clean, chunk, embed pipeline, Celery task | `ingest_document(document_id)` | `core`, `db`, `embeddings` |
| `embeddings` | ONNX encoder, tokenizer, ONNX reranker | `Encoder.encode`, `Reranker.score`, `count_tokens` | `core` |
| `retrieval` | dense, keyword, fusion, rerank stage, access filter | `retrieve(query, user, config)` | `core`, `db`, `embeddings` |
| `router` | classify a question into a path | `route(question)` | `core`, `llm`, `prompts` |
| `sql` | generate, validate, execute read-only SQL | `answer_structured(question, user)` | `core`, `db`, `llm`, `prompts` |
| `llm` | provider adapters, retries, cost accounting | `LLMClient.complete(request)` | `core` |
| `prompts` | load, register, render, bundle prompts | `get_active(name)`, `render(prompt, variables)` | `core`, `db` |
| `context` | token budget and evidence packing | `pack(evidence, budget)` | `core`, `embeddings` |
| `generation` | answer schema, generate, validate, repair | `generate_answer(question, evidence)` | `core`, `llm`, `prompts`, `context`, `guardrails` |
| `guardrails` | input checks, injection heuristics, citation and policy checks | `check_input`, `check_output` | `core` |
| `cache` | semantic cache | `lookup`, `store` | `core`, `embeddings` |
| `ratelimit` | token bucket and daily budget | `check_rate`, `consume_budget` | `core` |
| `observability` | trace writer, metrics | `TraceBuilder`, `record_metrics` | `core`, `db` |
| `evals` | golden set, metrics, judges, runner, reports, CLI | `run_eval(config)` | everything above through interfaces |

## Folder layout
```
src/docdesk/
  core/ db/ auth/ api/ ingestion/ embeddings/ retrieval/ router/ sql/
  llm/ prompts/ context/ generation/ guardrails/ cache/ ratelimit/
  observability/ evals/
prompts/            versioned prompt files (data, not code)
evals/              golden set, calibration set, baselines, reports
tests/              unit/ integration/ prompts/ evals/ fakes/ scripts/
frontend/           React app
scripts/            enforcement and helper scripts
docs/               this documentation
```

## Rules for module boundaries
- `evals` is the only module allowed to depend on nearly everything, and nothing depends on `evals`.
- No module imports from `api`. Routers call services, never the reverse.
- Data crosses boundaries as Pydantic models or plain dataclasses, never as ORM objects or raw dicts.
- Adding a module or a dependency edge needs a line in `DECISIONS.md`.
