# Eval report, run d0c644b8-1818-4f79-9f4a-1b54cc6f82c4

Config t111a_abstain060, split dev, mode full. Items run: 44. Items not run: 1.

Intervals are 95 percent bootstrap intervals of the mean, 2000 resamples, seed 0. Items that share a source document are resampled together. A cell shows n when some items had no value for it.

Headline: 13 of 30 answerable items pass strictly (faithfulness 1.0 and correctness 1.0), rate 0.43 [0.27, 0.60]. The overall pass rate is 0.57 [0.41, 0.70] over 44 items.

Unanswerable items pass by abstaining, so they raise the overall pass rate. The headline leaves them out.

## Results per category

| category | items | pass rate | recall@k | hit | MRR | context precision | citation precision | citation recall | faithfulness | correctness |
|---|---|---|---|---|---|---|---|---|---|---|
| single_fact | 19 | 0.63 [0.42, 0.84] | 0.84 [0.68, 1.00] | 0.84 [0.68, 1.00] | 0.76 [0.58, 0.92] | 0.18 [0.14, 0.22] | 0.89 [0.71, 1.00] (n=14) | 0.68 [0.47, 0.89] | 1.00 (all values equal) (n=14) | 0.68 [0.50, 0.87] |
| multi_chunk | 11 | 0.09 [0.00, 0.27] | 0.83 [0.70, 0.95] | 1.00 (all values equal) | 0.88 [0.70, 1.00] | 0.38 [0.33, 0.44] | 0.44 [0.00, 1.00] (n=3) | 0.14 [0.00, 0.36] | 1.00 (all values equal) (n=3) | 0.09 [0.00, 0.27] |
| unanswerable | 11 | 1.00 (all values equal) | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| adversarial | 3 | 0.33 [0.00, 1.00] | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| all | 44 | 0.57 [0.41, 0.70] | 0.84 [0.72, 0.94] (n=30) | 0.90 [0.80, 1.00] (n=30) | 0.81 [0.68, 0.92] (n=30) | 0.25 [0.21, 0.30] (n=30) | 0.81 [0.63, 0.96] (n=17) | 0.48 [0.32, 0.67] (n=30) | 1.00 (all values equal) (n=17) | 0.47 [0.28, 0.63] (n=30) |

## Abstain and refusal

| cell | items |
|---|---|
| correct abstain | 11 |
| wrong abstain | 13 |
| missed abstain | 0 |
| correct refusal | 1 |
| wrong refusal | 0 |
| missed refusal | 2 |
| system errors | 0 |

Abstention precision is the share of right abstains among abstains on items that are not refusal items. Abstention recall is the share of abstain items that abstained. The interval resamples items.

| rate | items | value |
|---|---|---|
| abstention precision | 24 | 0.46 [0.25, 0.67] |
| abstention recall | 11 | 1.00 (all values equal) |

## Failure labels

| label | items |
|---|---|
| context_overflow | 5 |
| ranking_miss | 5 |
| wrong_abstain | 3 |
| missed_refusal | 2 |
| retrieval_miss | 2 |
| context_distraction | 1 |
| incorrect | 1 |

## Judge failures

No judge parse failures or errors.

## Tokens and cost

Tokens in 45763, tokens out 9603, cost 0.03377565 USD, model calls 63, cache hits 63. Runs stored before T098b count judge cache hits only.

## Tokens and cost per model

This run only. Billed tokens were sent to the provider. Saved tokens were answered by the cache and cost nothing this run. Cost is the list price equivalent of the billed calls.

| model | calls | cached calls | tokens billed | tokens saved | cost billed USD |
|---|---|---|---|---|---|
| openai/gpt-oss-120b | 29 | 29 | 0 | 33600 | 0.000000 |
| qwen/qwen3.8-27b | 34 | 34 | 0 | 21766 | 0.000000 |

## Latency (non cached calls only)

Milliseconds per item. An item with any cached model call is left out of the generation, judge and total rows, because a cache hit has no real latency. Retrieval is never cached. Retrieval time includes the network round trip to the hosted database.

| stage | items | p50 ms | p95 ms |
|---|---|---|---|
| retrieval | 43 | 598 | 857 |
| generation | 14 | 0 | 0 |
| judge | 15 | 0 | 0 |
| total | 15 | 621 | 910 |

## Where answerable items fail

Answerable items that ran: 30. A failed item has one primary label.

| stage | items | labels |
|---|---|---|
| retrieval (gold not in top k) | 7 | ranking_miss 5, retrieval_miss 2 |
| packing (gold in top k, dropped before the prompt) | 5 | context_overflow 5 |
| generation (gold in the prompt) | 5 | context_distraction 1, incorrect 1, wrong_abstain 3 |
| pass | 13 |  |

Retrieval and packing together are the stages before the model: 12 of 30.

## Failure label by outcome

An answerable item that abstained is a wrong abstain, listed under its first label.

| label | answered | abstained | refused | error |
|---|---|---|---|---|
| retrieval_miss | 1 | 1 | 0 | 0 |
| ranking_miss | 0 | 5 | 0 | 0 |
| context_overflow | 1 | 4 | 0 | 0 |
| context_distraction | 1 | 0 | 0 | 0 |
| wrong_abstain | 0 | 3 | 0 | 0 |
| missed_refusal | 0 | 2 | 0 | 0 |
| incorrect | 1 | 0 | 0 | 0 |
| no label (passed) | 13 | 11 | 1 | 0 |

## Worst five answered items

Ranked by the lower of faithfulness and correctness, then by item id.

1. gi-039 (multi_chunk), label context_overflow: correctness 0.00 (0 covered, 2 missing, 0 contradicted), faithfulness 1.00 (3 of 3 claims supported), recall@k 1.00, 2 chunks in the prompt, 1 cited.
2. gi-047 (multi_chunk), label retrieval_miss: correctness 0.00 (0 covered, 2 missing, 0 contradicted), faithfulness 1.00 (13 of 13 claims supported), recall@k 0.50, 3 chunks in the prompt, 3 cited.
3. gi-017 (single_fact), label incorrect: correctness 0.50 (1 covered, 1 missing, 0 contradicted), faithfulness 1.00 (3 of 3 claims supported), recall@k 1.00, 5 chunks in the prompt, 1 cited.
4. gi-032 (single_fact), label context_distraction: correctness 0.50 (1 covered, 1 missing, 0 contradicted), faithfulness 1.00 (1 of 1 claims supported), recall@k 1.00, 2 chunks in the prompt, 1 cited.
5. gi-001 (single_fact), label none: correctness 1.00 (4 covered, 0 missing, 0 contradicted), faithfulness 1.00 (4 of 4 claims supported), recall@k 1.00, 5 chunks in the prompt, 1 cited.

## Not run

- gi-079: not run, needs T122
