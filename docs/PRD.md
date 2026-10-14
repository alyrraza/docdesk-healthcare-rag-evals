# Product requirements: DocDesk v2

Created 2026-10-13. Supersedes `DOCDESK_PROJECT_KICKOFF.md` (v1, Stripe version).
Every criterion below is written so a command can decide pass or fail. A test whose name
contains the criterion id covers it. Criteria without a test are not done.
Format: WHEN <trigger> THE system SHALL <response>.

## Product
A healthcare question answering service. Users upload documents and ask questions. The service
answers from unstructured documents (drug labels, health topics, guidelines) and from structured
synthetic patient tables, always with citations, and abstains when the evidence is weak. A built-in
evaluation harness measures accuracy, hallucination, abstention, latency and cost, and compares RAG
techniques and prompt versions. All data is public or synthetic. Every answer carries a disclaimer:
informational only, not medical advice.

## Users and roles
- `user`: registers, uploads documents, asks questions, sees own traces.
- `admin`: everything a user can, plus prompt version activation and the eval dashboard for all traces.

## Out of scope
Payments and billing, real patient data, multi-tenant organizations, personal diagnosis or dosing
advice, multi-turn conversation memory, real-time streaming answers.

## Auth and roles
- AC-AUTH-01: WHEN a user registers with a valid email and password THE system SHALL store a salted hash and never the password.
- AC-AUTH-02: WHEN valid credentials are posted to `/auth/login` THE system SHALL return a JWT with `sub`, `role` and `exp`.
- AC-AUTH-03: WHEN a protected route receives a missing, malformed or expired token THE system SHALL respond 401 in the standard error envelope.
- AC-AUTH-04: WHEN a non-admin calls an admin route THE system SHALL respond 403.
- AC-AUTH-05: THE system SHALL fail a test when any route is public and not in the public allowlist.

## Limits
- AC-LIM-01: WHEN a user exceeds the token bucket rate THE system SHALL respond 429 with `Retry-After`.
- AC-LIM-02: WHEN a user's daily token budget is exhausted THE system SHALL respond 429 with reason `budget_exhausted` and SHALL NOT call the LLM.
- AC-LIM-03: IF Redis is unreachable THEN THE system SHALL fail closed on the budget check (503) and fail open on the cache.

## Ingestion
- AC-ING-01: WHEN a PDF or text file is uploaded THE system SHALL return 202 with a document id and status `queued` without waiting for embedding.
- AC-ING-02: WHEN the worker finishes THE system SHALL set status `ready` and store the chunk count.
- AC-ING-03: IF parsing or embedding fails THEN THE system SHALL set status `failed` with a reason and store no partial chunks.
- AC-ING-04: WHEN the same user uploads identical content twice THE system SHALL NOT create duplicate chunks.
- AC-ING-05: THE system SHALL store on every chunk the document id, position, token count, chunker version and embedding model version.

## Retrieval
- AC-RET-01: THE system SHALL retrieve the dense top-N by cosine distance using pgvector.
- AC-RET-02: THE system SHALL retrieve the keyword top-N using Postgres full text search.
- AC-RET-03: WHEN hybrid retrieval is enabled THE system SHALL fuse both lists with reciprocal rank fusion, breaking ties by chunk id.
- AC-RET-04: WHEN the reranker is enabled THE system SHALL rerank the fused top-N to top-k.
- AC-RET-05: THE system SHALL return only chunks from documents the requesting user may access.

## Query and generation
- AC-GEN-01: THE system SHALL parse every model answer into the `AnswerOutput` schema.
- AC-GEN-02: THE system SHALL reject any answer that cites a chunk id not in the retrieved set.
- AC-GEN-03: WHEN the best retrieval score is below the abstain threshold THE system SHALL abstain without calling the generator.
- AC-GEN-04: IF output validation fails THEN THE system SHALL retry once with the validation error appended, then return the typed fallback with `abstain_reason = system_error`.
- AC-GEN-05: WHEN a question asks for a personal diagnosis or a dose THE system SHALL refuse with the policy message.
- AC-GEN-06: THE system SHALL append the disclaimer in code to every answer.

## Context
- AC-CTX-01: THE context packer SHALL never exceed the input token budget.
- AC-CTX-02: WHEN evidence does not fit THE packer SHALL drop the lowest ranked chunks first and record the dropped ids in the trace.
- AC-CTX-03: THE system SHALL wrap retrieved text in untrusted-data delimiters and never place it in the instruction section.

## Guardrails
- AC-GRD-01: WHEN a retrieved document contains an injected instruction THE system SHALL NOT follow it (measured on the adversarial slice).
- AC-GRD-02: WHEN a question exceeds the maximum length THE system SHALL reject it with 422.

## Structured data (SQL)
- AC-SQL-01: THE system SHALL execute only a single `SELECT` statement.
- AC-SQL-02: THE system SHALL execute only against allowlisted tables and columns.
- AC-SQL-03: THE system SHALL run SQL with a read-only database role, a row limit and a statement timeout.
- AC-SQL-04: WHEN SQL validation fails THE system SHALL NOT execute it and SHALL return a safe message.

## Router
- AC-RTR-01: THE router SHALL output exactly one of `documents`, `structured`, `both`.
- AC-RTR-02: IF the router fails THEN THE system SHALL fall back to `documents` and record it in the trace.

## Prompts
- AC-PRM-01: THE system SHALL treat a released prompt version as immutable.
- AC-PRM-02: WHEN an admin activates a prompt version THE system SHALL change only the active pointer, with no deploy.
- AC-PRM-03: THE system SHALL record the prompt bundle id (prompt version, model, parameters, schema version) on every trace.
- AC-PRM-04: THE system SHALL have prompt unit tests for every active prompt.

## Cache
- AC-CAC-01: WHEN a new question's similarity to a cached question is above the threshold AND the prompt bundle and document scope match THE system SHALL return the cached answer.
- AC-CAC-02: THE system SHALL store the original trace id on every cached answer.

## Observability
- AC-OBS-01: THE system SHALL write one trace row per request with stage latencies, tokens in and out, cost, prompt bundle id, config id, retrieved ids, dropped ids, cache hit and guardrail outcomes.
- AC-OBS-02: THE system SHALL expose latency histograms, token counters, cache hits and errors at `/metrics`.
- AC-OBS-03: THE system SHALL compute cost per query from token usage and a versioned price table.

## Evaluation
- AC-EVL-01: THE golden set file SHALL validate against its schema, and every item SHALL carry `verified_by` and `verified_on`.
- AC-EVL-02: THE runner SHALL compute retrieval metrics (recall@k, MRR, hit rate) without any LLM call.
- AC-EVL-03: THE runner SHALL assign exactly one primary failure label to every failed item.
- AC-EVL-04: THE runner SHALL cache every LLM call on disk by hash of prompt, model and parameters.
- AC-EVL-05: THE report SHALL show a bootstrap confidence interval for every headline metric.
- AC-EVL-06: WHEN a gated metric regresses beyond tolerance against the stored baseline THE CI job SHALL fail.
- AC-EVL-07: THE calibration report SHALL show raw agreement, Cohen's kappa and a bootstrap interval for each judge.
- AC-EVL-08: THE runner SHALL tie every run to its config, prompts, judge model and item set, and SHALL refuse to start or resume a run whose pins differ.

## Frontend
- AC-FE-01: THE user SHALL be able to register, log in and log out.
- AC-FE-02: WHEN an answer is shown THE UI SHALL list its citations and reveal the source chunk text on click.
- AC-FE-03: THE dashboard SHALL show p50 and p95 per stage, cost per query and failure causes.

## Delivery
- AC-DKR-01: THE CI SHALL build the API and worker Docker images on every push to main.

## Non-functional targets
Latency and cost targets are NOT invented now. They are set at the end of Phase 4 from measured
baseline numbers, then written here with the date.

## Success metric (the README hero)
One results table: every configuration in the technique matrix with recall@5, MRR, faithfulness,
answer correctness, citation accuracy, abstention precision and recall, p95 latency, cost per
query, each with an interval, plus a quality versus cost versus latency plot.
