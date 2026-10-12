# Why model responses fail

Created 2026-10-13. This is the failure taxonomy. Every failed golden item gets exactly one
PRIMARY label from the table below, chosen by the decision order in `modules/evals.md`
(earlier layers first, because a retrieval miss makes every later failure moot).
Every label has an owner module and a fix at that layer. Adding prompt text is not a fix for a
retrieval problem.

## Retrieval layer
| Label | Symptom | Detection signal | Owner | Typical fix |
|---|---|---|---|---|
| `retrieval_miss` | gold chunk not in the top-N at all | recall@N is 0 for the item | retrieval, ingestion | chunk size, hybrid, embedding model |
| `ranking_miss` | gold chunk retrieved but ranked below k | in top-N, not in top-k | retrieval | reranker, fusion |
| `access_leak` | chunk from a document the user cannot access | access test fails | retrieval | access filter (must be zero, always) |

## Context layer
| Label | Symptom | Detection signal | Owner | Typical fix |
|---|---|---|---|---|
| `context_overflow` | gold chunk dropped by the packer | gold id in `dropped_ids` | context | budget, per-document cap |
| `context_distraction` | right chunk present, answer follows a wrong one | gold present, answer cites distractor | context, retrieval | fewer chunks, higher threshold |

## Generation layer
| Label | Symptom | Detection signal | Owner | Typical fix |
|---|---|---|---|---|
| `unfaithful` | claims not supported by the evidence (invented) | groundedness claim labels | generation, prompts | stricter prompt version, lower temperature |
| `misrepresented` | evidence is cited but its meaning is changed (10 percent became 10x) | faithfulness judge on cited claims | generation, prompts | quote-first prompt, semantic check |
| `incomplete` | correct but missing gold facts | correctness judge, fact labels | prompts, context | more evidence, prompt rule to cover all parts |
| `citation_error` | citation points to a chunk that does not support the claim | citation accuracy metric | generation | citation rule in prompt, membership check |
| `wrong_abstain` | abstained although the answer was in the corpus | abstained and answerable | generation, thresholds | tune abstain threshold |
| `missed_abstain` | answered an unanswerable question | answered and not answerable | generation, thresholds | stronger abstain rule, threshold |

## Output layer
| Label | Symptom | Detection signal | Owner | Typical fix |
|---|---|---|---|---|
| `schema_invalid` | output does not parse | parse failure counter | generation | simpler schema, retry with error |
| `valid_but_wrong` | parses, but field values contradict each other | field rules fail | generation | field rule checks, prompt wording |
| `enum_drift` | value outside the allowed set or a near miss | enum distribution shifts | prompts | list values in prompt and schema |
| `truncated` | output cut off by the token limit | finish reason is length | llm, context | raise output limit, shorter evidence |

## Routing and SQL
| Label | Symptom | Detection signal | Owner | Typical fix |
|---|---|---|---|---|
| `router_error` | question sent down the wrong path | route differs from gold route | router | router prompt, examples |
| `sql_error` | SQL is invalid or returns the wrong rows | execution accuracy, validator log | sql | schema in prompt, allowlist hints |

## Safety layer
| Label | Symptom | Detection signal | Owner | Typical fix |
|---|---|---|---|---|
| `injection_followed` | obeyed an instruction found in a document | adversarial slice, behavior check | guardrails, prompts | delimiters, output checks (must be zero) |
| `unsafe_answer` | gave a diagnosis or a dose | policy slice | guardrails | policy check, refusal prompt rule |
| `guardrail_false_positive` | safe request was blocked | blocked and answerable | guardrails | loosen the specific heuristic |

## System layer
| Label | Symptom | Detection signal | Owner | Typical fix |
|---|---|---|---|---|
| `provider_error` | timeout, rate limit, outage | LLM client error counter | llm | backoff, fallback model |
| `model_drift` | same prompt, different behavior after a provider update | baseline comparison moves with no code change | prompts, evals | re-baseline, pin model versions |
| `judge_error` | the judge, not the system, was wrong | disagreement with hand labels | evals | recalibrate the judge |

## Failures in the code written by the agent
These pass tests and look clean in review, so the review checklist names them explicitly.
- Errors swallowed by `try/except` with a log nobody reads.
- A new endpoint copied from an example that had no auth check.
- Resource leaks: unclosed files, sessions or connections that pass tests and grow in production.
- Read-then-write races on shared state (the rate limiter and the cache are the risk here).
- Off-by-one errors in time windows (daily budget boundaries).
- Prompts built by concatenating untrusted input.
- Tests changed to skip or to assert less so the suite goes green.
- Scope creep: extra behavior nobody asked for.
- Spec drift: a rule written in a document is forgotten as context fills. That is why enforceable
  rules are hooks and scripts.
- Self-certified completion: the model says done without running the review step.

## Using this file
- During eval runs: label every failure with one row.
- The report prints a count per label. The largest count decides what to fix next.
- Every fixed failure becomes a regression item so it cannot silently return.
