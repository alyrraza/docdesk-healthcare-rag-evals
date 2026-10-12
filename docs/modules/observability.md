# Module: observability, cache and rate limiting

Created 2026-10-13. Criteria: AC-OBS-01 to 03, AC-CAC-01 and 02, AC-LIM-01 to 03.

## Trace (`observability/trace.py`)
`TraceBuilder` is created at the start of a request and collects fields as stages finish. It is written
once at the end, even on error (try/finally). One row per request (AC-OBS-01).

Fields: trace id, user id, timestamp, question hash (the question text is stored only if the user allows it),
route, config id, prompt bundle id, retrieved ids with scores, used ids, dropped ids, per stage latency
(auth, limits, router, embed, vector search, keyword search, fusion, rerank, pack, llm, validate, total),
tokens in and out per LLM call and by context slot, cost, cache hit and the source trace id,
guardrail outcomes, validation layers passed, retry used, abstained and reason, finish reason, error code.

Timings use a monotonic clock. Database time is its own stage, so a hosted database's network round
trip is visible and not blamed on the model.

## Metrics (`observability/metrics.py`, AC-OBS-02)
Prometheus histograms per stage, counters for tokens, cost, cache hits, errors, retries and fallbacks,
a gauge for queue depth. Exposed at `/metrics`. Grafana is an optional compose service, never run locally.
The dashboard page in the frontend reads the trace table directly.

## Cost (`llm/cost.py`, AC-OBS-03)
Price table with a model name, input and output price and an effective date. Cost is computed from the
token usage the provider reports. Unknown model means cost is null and an alert counter increments, never a guess.

## Semantic cache (`cache/semantic.py`)
- Key: normalized question embedding. Lookup: nearest cached question in Redis.
- A hit requires similarity above the threshold AND the same prompt bundle id AND the same document scope (AC-CAC-01).
- A cached answer stores its original trace id (AC-CAC-02).
- Risk: a similar but different question gets a wrong answer. Experiment E10 measures wrong cache hits on the
  golden set before the cache is enabled by default. Start the threshold strict.
- Never cache a fallback, an abstain caused by a system error, or an answer from a guardrail block.
- Redis down: cache is bypassed (fail open).

## Rate limit and budget (`ratelimit/`)
- `token_bucket.py`: built from scratch on Redis. A Lua script performs refill and take atomically, so two
  concurrent requests cannot both take the last token (the read-then-write race). Returns allowed or the wait
  time for `Retry-After` (AC-LIM-01).
- `budget.py`: daily token budget per user. The window boundary is explicit (UTC midnight) and tested at the edge.
  Estimated tokens are reserved before the LLM call and reconciled after it (AC-LIM-02).
- Redis down: the budget check fails closed with 503 so cost cannot run away (AC-LIM-03).
Security-sensitive: after writing, explain the bucket and the Lua script line by line to Ali.

## Edge cases
- Clock skew and window boundaries for the daily budget.
- A request that fails after reserving budget: reconcile so the user is not charged for nothing.
- Trace write failing must never fail the user request: log and count it.
- Metrics label cardinality: never use user id or question text as a label.

## Tests
Bucket: sequential and concurrent takes, refill over time with a fake clock. Budget: boundary at midnight,
reserve and reconcile. Cache: hit, miss, bundle mismatch, scope mismatch. Trace: one row per request even on
error. Cost: known token counts give known cost, unknown model gives null.
