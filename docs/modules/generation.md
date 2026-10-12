# Module: generation (llm, prompts, context, generation, guardrails)

Created 2026-10-13. Criteria: AC-GEN-01 to 06, AC-CTX-01 to 03, AC-GRD-01 and 02, AC-PRM-01 to 04.
Read with `CONTEXT.md`, `OUTPUTS.md`, `PROMPT_STANDARD.md`. Experiments: E8 prompt version, E9 generator model.

## llm
- `client.py`: `LLMClient.complete(request) -> LLMResult`. One interface for every provider.
  `LLMResult` carries text, tokens in and out, latency, finish reason, model name, cost.
- `providers/`: one adapter file per provider. Each maps the common request to the provider call.
- `retry.py`: backoff on rate limit and timeout, a hard cap on attempts, a per-call timeout.
- `cost.py`: price table keyed by model with an effective date. Cost is computed in code (AC-OBS-03).
- Generator and judge use different models. A config check fails startup if they are the same.

## prompts
- `loader.py`: reads prompt files from `prompts/`, parses front matter, computes the content hash.
- `registry.py`: syncs files into `prompt_versions`, resolves the active version per name via `active_prompts`.
- `renderer.py`: fills `{{variables}}`. Variables listed as `untrusted` are wrapped in delimiters with
  escaped delimiter strings. Rejects unfilled variables. This is the only place prompts are assembled.
- `bundle.py`: builds the bundle id from prompt version, model, params, schema version and retrieval config id.

## context
- `budget.py`: slot budgets from `CONTEXT.md`. `packer.py`: the packing algorithm. Never exceeds the
  budget (AC-CTX-01), records used and dropped ids (AC-CTX-02).

## guardrails
- `input.py`: max length (AC-GRD-02), simple PII flag, injection heuristics (known phrases, role
  override attempts), policy check for diagnosis and dose requests (AC-GEN-05).
- `output.py`: schema parse, field rules, semantic checks, in the three layers from `OUTPUTS.md`.
- `citations.py`: citation membership check (AC-GEN-02).
- `policy.py`: the refusal text and the disclaimer text. The disclaimer is appended by code (AC-GEN-06).
- Heuristics are a first filter, not the defense. Defense in depth: delimiters, output checks, no tools given to the model.

## generation
- `schema.py`: Pydantic models from `OUTPUTS.md`.
- `answer.py`: `generate_answer(question, evidence, bundle) -> AnswerResult`. Steps: abstain check,
  pack, render, call, validate, retry once with the validation error, typed fallback.
- `repair.py`: builds the retry prompt (original request plus the exact validation error).

## Prompt files shipped in `prompts/`
`answer.v1` (strict citations and abstain), `router.v1`, `text2sql.v1`, `judge_faithfulness.v1`,
`judge_correctness.v1`. New versions are added through experiment E8 and recipe S3.

## Edge cases
- Provider returns an empty string, a refusal, or text that ends mid-JSON: counts as `schema_invalid` or `truncated`.
- Evidence contains the delimiter string: escaped by the renderer.
- Question in Roman Urdu or another language: out of scope for v2, answer with `out_of_scope`.
- Conflicting chunks: the answer prompt tells the model to state the conflict and cite both.

## Tests
Unit with a fake LLM: schema validation, retry once then fallback, citation membership, packer budget
(property tests), renderer escaping, disclaimer always present, guardrail heuristics. Prompt tests per
`PROMPT_STANDARD.md`. The adversarial slice in the golden set measures AC-GRD-01 end to end.
