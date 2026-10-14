# Eval report, run 40488aff-a8dd-4605-a009-a1e9d674edfc

Config b0, split test, mode full. Items run: 29. Items not run: 1.

Intervals are 95 percent bootstrap intervals of the mean, 2000 resamples, seed 0. Items that share a source document are resampled together. A cell shows n when some items had no value for it.

Headline: 13 of 20 answerable items pass strictly (faithfulness 1.0 and correctness 1.0), rate 0.65 [0.45, 0.85]. The overall pass rate is 0.76 [0.59, 0.90] over 29 items.

Unanswerable items pass by abstaining, so they raise the overall pass rate. The headline leaves them out.

## Results per category

| category | items | pass rate | recall@k | hit | MRR | context precision | citation precision | citation recall | faithfulness | correctness |
|---|---|---|---|---|---|---|---|---|---|---|
| single_fact | 12 | 1.00 (all values equal) | 1.00 (all values equal) | 1.00 (all values equal) | 0.90 [0.76, 1.00] | 0.20 (all values equal) | 0.88 [0.67, 1.00] | 0.92 [0.75, 1.00] | 1.00 (all values equal) | 1.00 (all values equal) |
| multi_chunk | 8 | 0.12 [0.00, 0.38] | 0.62 [0.38, 0.81] | 0.88 [0.62, 1.00] | 0.71 [0.43, 0.94] | 0.30 [0.18, 0.43] | 0.83 [0.50, 1.00] (n=3) | 0.25 [0.00, 0.50] | 0.97 [0.91, 1.00] (n=3) | 0.25 [0.00, 0.50] |
| unanswerable | 8 | 1.00 (all values equal) | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| adversarial | 1 | 1.00 (all values equal) | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| all | 29 | 0.76 [0.59, 0.90] | 0.85 [0.70, 0.95] (n=20) | 0.95 [0.85, 1.00] (n=20) | 0.83 [0.68, 0.95] (n=20) | 0.24 [0.19, 0.30] (n=20) | 0.87 [0.70, 1.00] (n=15) | 0.65 [0.45, 0.85] (n=20) | 0.99 [0.98, 1.00] (n=15) | 0.70 [0.50, 0.90] (n=20) |

## Abstain and refusal

| cell | items |
|---|---|
| correct abstain | 8 |
| wrong abstain | 5 |
| missed abstain | 0 |
| correct refusal | 1 |
| wrong refusal | 0 |
| missed refusal | 0 |
| system errors | 0 |

Abstention precision is the share of right abstains among abstains on items that are not refusal items. Abstention recall is the share of abstain items that abstained. The interval resamples items.

| rate | items | value |
|---|---|---|
| abstention precision | 13 | 0.62 [0.38, 0.85] |
| abstention recall | 8 | 1.00 (all values equal) |

## Failure labels

| label | items |
|---|---|
| ranking_miss | 4 |
| context_overflow | 2 |
| retrieval_miss | 1 |

## Judge failures

No judge parse failures or errors.

## Tokens and cost

Tokens in 44870, tokens out 9149, cost 0.03145520 USD, model calls 58, cache hits 0. Runs stored before T098b count judge cache hits only.

## Tokens and cost per model

This run only. Billed tokens were sent to the provider. Saved tokens were answered by the cache and cost nothing this run. Cost is the list price equivalent of the billed calls.

| model | calls | cached calls | tokens billed | tokens saved | cost billed USD |
|---|---|---|---|---|---|
| openai/gpt-oss-120b | 28 | 0 | 34157 | 0 | 0.008206 |
| qwen/qwen3.8-27b | 30 | 0 | 19862 | 0 | 0.023250 |

Billed tokens per key slot of the key pool (slot numbers only, never keys).

| model | key slot | tokens billed |
|---|---|---|
| openai/gpt-oss-120b | 1 | 1052 |
| openai/gpt-oss-120b | 2 | 33105 |
| qwen/qwen3.8-27b | 1 | 19862 |

## Latency (non cached calls only)

Milliseconds per item. An item with any cached model call is left out of the generation, judge and total rows, because a cache hit has no real latency. Retrieval is never cached. Retrieval time includes the network round trip to the hosted database.

| stage | items | p50 ms | p95 ms |
|---|---|---|---|
| retrieval | 28 | 916 | 2841 |
| generation | 28 | 1351 | 26396 |
| judge | 15 | 1026 | 38356 |
| total | 29 | 4111 | 41609 |

## Where answerable items fail

Answerable items that ran: 20. A failed item has one primary label.

| stage | items | labels |
|---|---|---|
| retrieval (gold not in top k) | 5 | ranking_miss 4, retrieval_miss 1 |
| packing (gold in top k, dropped before the prompt) | 2 | context_overflow 2 |
| generation (gold in the prompt) | 0 |  |
| pass | 13 |  |

Retrieval and packing together are the stages before the model: 7 of 20.

## Failure label by outcome

An answerable item that abstained is a wrong abstain, listed under its first label.

| label | answered | abstained | refused | error |
|---|---|---|---|---|
| retrieval_miss | 0 | 1 | 0 | 0 |
| ranking_miss | 1 | 3 | 0 | 0 |
| context_overflow | 1 | 1 | 0 | 0 |
| no label (passed) | 13 | 8 | 1 | 0 |

## Worst five answered items

Ranked by the lower of faithfulness and correctness, then by item id.

1. gi-052 (multi_chunk), label ranking_miss: correctness 0.00 (0 covered, 2 missing, 0 contradicted), faithfulness 1.00 (3 of 3 claims supported), recall@k 0.50, 2 chunks in the prompt, 2 cited.
2. gi-038 (multi_chunk), label context_overflow: correctness 1.00 (2 covered, 0 missing, 0 contradicted), faithfulness 0.91 (10 of 11 claims supported), recall@k 1.00, 2 chunks in the prompt, 1 cited.
3. gi-004 (single_fact), label none: correctness 1.00 (3 covered, 0 missing, 0 contradicted), faithfulness 1.00 (6 of 6 claims supported), recall@k 1.00, 2 chunks in the prompt, 1 cited.
4. gi-011 (single_fact), label none: correctness 1.00 (2 covered, 0 missing, 0 contradicted), faithfulness 1.00 (1 of 1 claims supported), recall@k 1.00, 2 chunks in the prompt, 1 cited.
5. gi-012 (single_fact), label none: correctness 1.00 (1 covered, 0 missing, 0 contradicted), faithfulness 1.00 (1 of 1 claims supported), recall@k 1.00, 2 chunks in the prompt, 1 cited.

## Not run

- gi-078: not run, needs T122
