# Context management

Created 2026-10-13. How the model's input is assembled for each request. The context window is
a capped per-request budget, not a bucket to fill. Every token of evidence either helps the answer
or distracts from it. The assembly steps are: select, compress, order, isolate.

## Budget per slot (starting values, tune with experiment E5)
Total input budget: 6000 tokens. These numbers are starting points, not facts. Record the tuned
values and the measured effect in `DECISIONS.md`.

| Slot | Budget | Notes |
|---|---|---|
| System rules and policy | 500 | stable text, identical across requests |
| Output schema and instructions | 300 | stable text |
| Evidence (retrieved chunks or SQL rows) | 4200 | the only large, dynamic slot |
| Conversation history | 0 | single turn in v2, on purpose (see below) |
| Question | 300 | hard length limit enforced before this point |
| Reserve | 700 | headroom so a long question never causes truncation |

## Order inside the prompt
1. Stable prefix first: system rules, policy, schema. Identical bytes on every request, so a
   provider that supports prefix caching can reuse it. Cached prefixes are reported to cost roughly
   ten times less than fresh input. Verify the real discount with your provider before relying on it.
2. Evidence next, inside untrusted-data delimiters, each item labeled with a short stable id such as `[c1]`.
3. The question last, followed by the output instruction.
This order is a starting design. Measure it: the eval harness can compare it to alternatives.

## Packing algorithm (`context/packer.py`)
1. Take the ranked evidence list from retrieval (or SQL rows).
2. Drop items below the relevance threshold. Threshold is tuned on the dev split, not copied from a blog.
3. Remove near duplicate chunks (same document and overlapping text).
4. Cap chunks per document so one long document cannot crowd out everything else.
5. Add items in rank order until the evidence budget is reached. Never cut a chunk in half.
6. Record the used ids and the dropped ids in the trace (AC-CTX-02).
7. If nothing survives, return an empty pack. The caller abstains with `no_evidence`.

## Untrusted data
Evidence goes in only through `prompts/renderer.py`. The renderer wraps each item in delimiters,
states in the system rules that text inside the delimiters is data and never instructions, and
escapes any delimiter strings found inside the evidence itself. The adversarial golden items test
this (AC-GRD-01). Delimiters reduce risk. They do not eliminate it, so the output guardrails still
check citations and policy.

## Context failure modes and what this design does about each
| Failure | What it is | Our defense |
|---|---|---|
| Poisoning | a wrong or injected statement enters the context and gets repeated | untrusted delimiters, citation membership check, adversarial slice |
| Distraction | too much text pulls the model away from the question | small evidence budget, relevance threshold, top-k kept low |
| Confusion | irrelevant material is mistaken for something to use | dedupe, per-document cap, reranker experiment E4 |
| Clash | contradictory pieces of context | single turn (no accumulated history), conflicting chunks surfaced in the answer by the prompt rule |
| Rot | quality degrades as input length grows | evidence budget stays small, measured in E5 with 3, 5, 10 chunks |

Numbers quoted in blogs about these failures come from specific models and older benchmarks. Treat
them as directional. Our own measurements in E5 are the evidence that counts.

## Why single turn
Multi-turn history adds context clash and needs compaction rules. It is parked in `DECISIONS.md`.
If it is added later: summarize history once it passes a set size, keep decisions and the current
objective, drop raw tool output, and add a multi-turn slice to the golden set first.

## Telemetry (written on every trace)
Tokens by slot, evidence ids used and dropped, context precision when gold ids are known
(eval runs), prefix cache hit if the provider reports it, and total input tokens against the budget.

## Tests
AC-CTX-01 (never exceeds budget, including property tests with random inputs), AC-CTX-02 (drop order),
AC-CTX-03 (delimiters present, delimiter injection escaped).
