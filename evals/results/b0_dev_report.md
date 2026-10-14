# Eval report, run dfaad803-c59e-466c-8e2e-609471d82cee

Config b0, split dev, mode full. Items run: 44. Items not run: 1.

Intervals are 95 percent bootstrap intervals of the mean, 2000 resamples, seed 0. Items that share a source document are resampled together. A cell shows n when some items had no value for it.

## Results per category

| category | items | pass rate | recall@k | hit | MRR | context precision | citation precision | citation recall | faithfulness | correctness |
|---|---|---|---|---|---|---|---|---|---|---|
| single_fact | 19 | 0.74 [0.53, 0.95] | 0.84 [0.68, 1.00] | 0.84 [0.68, 1.00] | 0.76 [0.58, 0.92] | 0.18 [0.14, 0.22] | 0.88 [0.72, 1.00] (n=16) | 0.79 [0.58, 0.95] | 1.00 [1.00, 1.00] (n=16) | 0.79 [0.61, 0.95] |
| multi_chunk | 11 | 0.09 [0.00, 0.27] | 0.83 [0.70, 0.95] | 1.00 [1.00, 1.00] | 0.88 [0.70, 1.00] | 0.38 [0.33, 0.44] | 0.58 [0.17, 1.00] (n=4) | 0.23 [0.00, 0.45] | 0.92 [0.75, 1.00] (n=4) | 0.18 [0.00, 0.45] |
| unanswerable | 11 | 1.00 [1.00, 1.00] | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| adversarial | 3 | 0.33 [0.00, 1.00] | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| all | 44 | 0.61 [0.48, 0.75] | 0.84 [0.72, 0.94] (n=30) | 0.90 [0.80, 1.00] (n=30) | 0.81 [0.68, 0.92] (n=30) | 0.25 [0.21, 0.30] (n=30) | 0.82 [0.66, 0.95] (n=20) | 0.58 [0.40, 0.75] (n=30) | 0.98 [0.95, 1.00] (n=20) | 0.57 [0.38, 0.73] (n=30) |

## Abstain and refusal

| cell | items |
|---|---|
| correct abstain | 11 |
| wrong abstain | 10 |
| missed abstain | 0 |
| correct refusal | 1 |
| wrong refusal | 0 |
| missed refusal | 2 |
| system errors | 0 |

## Failure labels

| label | items |
|---|---|
| context_overflow | 5 |
| ranking_miss | 5 |
| missed_refusal | 2 |
| retrieval_miss | 2 |
| context_distraction | 1 |
| incorrect | 1 |
| unfaithful | 1 |

## Judge failures

No judge parse failures or errors.

## Tokens and cost

Tokens in 65525, tokens out 12867, cost 0.04197910 USD, model calls 83, cache hits 2.

## Pass rate on answerable items

Pass means faithfulness 1.0 and correctness 1.0. 15 of 30 answerable items pass (0.50). The category tables above use the harness pass flag, which also counts a correct abstain or refusal as a pass.

## Where answerable items fail

Answerable items that ran: 30. A failed item has one primary label.

| stage | items | labels |
|---|---|---|
| retrieval (gold not in top 5) | 7 | retrieval_miss 2, ranking_miss 5 |
| packing (gold in top 5, dropped before the prompt) | 5 | context_overflow 5 |
| generation (gold in the prompt) | 3 | incorrect 1, context_distraction 1, unfaithful 1 |
| pass | 15 | |

Retrieval and packing together are the stages before the model: 12 of 30.

## Tokens and cost per model

Counted from the cache entries written by the real calls of this session (smoke items included, because the full run reused them). The ledger column is the guard's count for the last 24 hours.

| model | calls | tokens in | tokens out | cost USD | ledger tokens | guard left |
|---|---|---|---|---|---|---|
| openai/gpt-oss-120b | 43 | 42466 | 10090 | 0.012424 | 52556 | 117444 |
| qwen/qwen3.8-27b | 40 | 23059 | 2777 | 0.029555 | 25836 | 144164 |

## Five worst answered items

Ranked by the lower of faithfulness and correctness, then by item id.

1. gi-039 (multi_chunk), label context_overflow: correctness 0.00 (0 covered, 2 missing, 0 contradicted), faithfulness 1.00 (3 supported of 3 claims), recall@5 1.00, 2 chunks in the prompt, 1 cited.
2. gi-047 (multi_chunk), label retrieval_miss: correctness 0.00 (0 covered, 2 missing, 0 contradicted), faithfulness 1.00 (13 supported of 13 claims), recall@5 0.50, 3 chunks in the prompt, 3 cited.
3. gi-017 (single_fact), label incorrect: correctness 0.50 (1 covered, 1 missing, 0 contradicted), faithfulness 1.00 (3 supported of 3 claims), recall@5 1.00, 5 chunks in the prompt, 1 cited.
4. gi-032 (single_fact), label context_distraction: correctness 0.50 (1 covered, 1 missing, 0 contradicted), faithfulness 1.00 (1 supported of 1 claims), recall@5 1.00, 2 chunks in the prompt, 1 cited.
5. gi-044 (multi_chunk), label unfaithful: correctness 1.00 (2 covered, 0 missing, 0 contradicted), faithfulness 0.67 (2 supported of 3 claims), recall@5 1.00, 4 chunks in the prompt, 2 cited.

## Not run

gi-079 (injected instruction, needs T122) is the only dev item not run. Dev has 45 verified items, not 60.
