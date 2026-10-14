# Eval report, run 6e8a809d-34b3-41c4-8ca5-56eb634d0134

Config final, split test, mode full. Items run: 29. Items not run: 1.

Intervals are 95 percent bootstrap intervals of the mean, 2000 resamples, seed 0. Items that share a source document are resampled together. A cell shows n when some items had no value for it.

Headline: 15 of 20 answerable items pass strictly (faithfulness 1.0 and correctness 1.0), rate 0.75 [0.55, 0.95]. The overall pass rate is 0.83 [0.69, 0.97] over 29 items.

Unanswerable items pass by abstaining, so they raise the overall pass rate. The headline leaves them out.

## Results per category

| category | items | pass rate | recall@k | hit | MRR | context precision | citation precision | citation recall | faithfulness | correctness |
|---|---|---|---|---|---|---|---|---|---|---|
| single_fact | 12 | 1.00 (all values equal) | 1.00 (all values equal) | 1.00 (all values equal) | 0.90 [0.76, 1.00] | 0.20 (all values equal) | 1.00 (all values equal) | 1.00 (all values equal) | 1.00 (all values equal) | 1.00 (all values equal) |
| multi_chunk | 8 | 0.38 [0.00, 0.75] | 0.62 [0.38, 0.81] | 0.88 [0.62, 1.00] | 0.71 [0.43, 0.94] | 0.30 [0.18, 0.43] | 0.60 [0.30, 0.90] (n=5) | 0.38 [0.12, 0.69] | 1.00 (all values equal) (n=5) | 0.44 [0.12, 0.75] |
| unanswerable | 8 | 1.00 (all values equal) | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| adversarial | 1 | 1.00 (all values equal) | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| all | 29 | 0.83 [0.69, 0.97] | 0.85 [0.70, 0.95] (n=20) | 0.95 [0.85, 1.00] (n=20) | 0.83 [0.68, 0.95] (n=20) | 0.24 [0.19, 0.30] (n=20) | 0.88 [0.74, 1.00] (n=17) | 0.75 [0.57, 0.93] (n=20) | 1.00 (all values equal) (n=17) | 0.78 [0.57, 0.95] (n=20) |

## Abstain and refusal

| cell | items |
|---|---|
| correct abstain | 8 |
| wrong abstain | 3 |
| missed abstain | 0 |
| correct refusal | 1 |
| wrong refusal | 0 |
| missed refusal | 0 |
| system errors | 0 |

Abstention precision is the share of right abstains among abstains on items that are not refusal items. Abstention recall is the share of abstain items that abstained. The interval resamples items.

| rate | items | value |
|---|---|---|
| abstention precision | 11 | 0.73 [0.45, 1.00] |
| abstention recall | 8 | 1.00 (all values equal) |

## Failure labels

| label | items |
|---|---|
| ranking_miss | 3 |
| incorrect | 1 |
| retrieval_miss | 1 |

## Judge failures

No judge parse failures or errors.

## Tokens and cost

Tokens in 55976, tokens out 9704, cost 0.03777675 USD, model calls 62, cache hits 26. Runs stored before T098b count judge cache hits only.

## Tokens and cost per model

This run only. Billed tokens were sent to the provider. Saved tokens were answered by the cache and cost nothing this run. Cost is the list price equivalent of the billed calls.

| model | calls | cached calls | tokens billed | tokens saved | cost billed USD |
|---|---|---|---|---|---|
| openai/gpt-oss-120b | 28 | 12 | 23058 | 16774 | 0.005696 |
| qwen/qwen3.8-27b | 34 | 14 | 15972 | 9876 | 0.017722 |

Billed tokens per key slot of the key pool (slot numbers only, never keys).

| model | key slot | tokens billed |
|---|---|---|
| openai/gpt-oss-120b | 2 | 23058 |
| qwen/qwen3.8-27b | 1 | 15972 |

## Latency (non cached calls only)

Milliseconds per item. An item with any cached model call is left out of the generation, judge and total rows, because a cache hit has no real latency. Retrieval is never cached. Retrieval time includes the network round trip to the hosted database.

| stage | items | p50 ms | p95 ms |
|---|---|---|---|
| retrieval | 28 | 826 | 1517 |
| generation | 14 | 1665 | 41947 |
| judge | 9 | 776 | 1066 |
| total | 15 | 3607 | 44030 |

## Where answerable items fail

Answerable items that ran: 20. A failed item has one primary label.

| stage | items | labels |
|---|---|---|
| retrieval (gold not in top k) | 4 | ranking_miss 3, retrieval_miss 1 |
| packing (gold in top k, dropped before the prompt) | 0 |  |
| generation (gold in the prompt) | 1 | incorrect 1 |
| pass | 15 |  |

Retrieval and packing together are the stages before the model: 4 of 20.

## Failure label by outcome

An answerable item that abstained is a wrong abstain, listed under its first label.

| label | answered | abstained | refused | error |
|---|---|---|---|---|
| retrieval_miss | 0 | 1 | 0 | 0 |
| ranking_miss | 1 | 2 | 0 | 0 |
| incorrect | 1 | 0 | 0 | 0 |
| no label (passed) | 15 | 8 | 1 | 0 |

## Worst five answered items

Ranked by the lower of faithfulness and correctness, then by item id.

1. gi-045 (multi_chunk), label incorrect: correctness 0.00 (0 covered, 2 missing, 0 contradicted), faithfulness 1.00 (2 of 2 claims supported), recall@k 1.00, 5 chunks in the prompt, 2 cited.
2. gi-052 (multi_chunk), label ranking_miss: correctness 0.50 (1 covered, 0 missing, 1 contradicted), faithfulness 1.00 (3 of 3 claims supported), recall@k 0.50, 4 chunks in the prompt, 2 cited.
3. gi-004 (single_fact), label none: correctness 1.00 (3 covered, 0 missing, 0 contradicted), faithfulness 1.00 (6 of 6 claims supported), recall@k 1.00, 4 chunks in the prompt, 1 cited.
4. gi-011 (single_fact), label none: correctness 1.00 (2 covered, 0 missing, 0 contradicted), faithfulness 1.00 (2 of 2 claims supported), recall@k 1.00, 4 chunks in the prompt, 1 cited.
5. gi-012 (single_fact), label none: correctness 1.00 (1 covered, 0 missing, 0 contradicted), faithfulness 1.00 (1 of 1 claims supported), recall@k 1.00, 4 chunks in the prompt, 1 cited.

## Not run

- gi-078: not run, needs T122
