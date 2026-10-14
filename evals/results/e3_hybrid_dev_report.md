# Eval report, run b509fe25-240f-4ecd-8aa5-753d0eca22ca

Config e3_hybrid, split dev, mode full. Items run: 44. Items not run: 1.

Intervals are 95 percent bootstrap intervals of the mean, 2000 resamples, seed 0. Items that share a source document are resampled together. A cell shows n when some items had no value for it.

Headline: 16 of 30 answerable items pass strictly (faithfulness 1.0 and correctness 1.0), rate 0.53 [0.37, 0.70]. The overall pass rate is 0.64 [0.50, 0.77] over 44 items.

Unanswerable items pass by abstaining, so they raise the overall pass rate. The headline leaves them out.

## Results per category

| category | items | pass rate | recall@k | hit | MRR | context precision | citation precision | citation recall | faithfulness | correctness |
|---|---|---|---|---|---|---|---|---|---|---|
| single_fact | 19 | 0.74 [0.53, 0.89] | 0.84 [0.68, 1.00] | 0.84 [0.68, 1.00] | 0.67 [0.48, 0.84] | 0.17 [0.14, 0.20] | 0.72 [0.53, 0.91] (n=16) | 0.68 [0.47, 0.89] | 1.00 (all values equal) (n=16) | 0.79 [0.61, 0.95] |
| multi_chunk | 11 | 0.18 [0.00, 0.45] | 0.79 [0.65, 0.92] | 1.00 (all values equal) | 0.67 [0.52, 0.82] | 0.36 [0.29, 0.44] | 0.83 [0.50, 1.00] (n=3) | 0.23 [0.00, 0.45] | 0.89 [0.67, 1.00] (n=3) | 0.27 [0.00, 0.55] |
| unanswerable | 11 | 1.00 (all values equal) | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| adversarial | 3 | 0.33 [0.00, 1.00] | n/a | n/a | n/a | n/a | n/a | n/a | 1.00 (all values equal) (n=1) | n/a |
| all | 44 | 0.64 [0.50, 0.77] | 0.82 [0.70, 0.93] (n=30) | 0.90 [0.80, 1.00] (n=30) | 0.67 [0.54, 0.79] (n=30) | 0.24 [0.19, 0.29] (n=30) | 0.74 [0.58, 0.89] (n=19) | 0.52 [0.33, 0.70] (n=30) | 0.98 [0.95, 1.00] (n=20) | 0.60 [0.42, 0.77] (n=30) |

## Abstain and refusal

| cell | items |
|---|---|
| correct abstain | 11 |
| wrong abstain | 11 |
| missed abstain | 0 |
| correct refusal | 1 |
| wrong refusal | 0 |
| missed refusal | 2 |
| system errors | 0 |

Abstention precision is the share of right abstains among abstains on items that are not refusal items. Abstention recall is the share of abstain items that abstained. The interval resamples items.

| rate | items | value |
|---|---|---|
| abstention precision | 22 | 0.50 [0.32, 0.68] |
| abstention recall | 11 | 1.00 (all values equal) |

## Failure labels

| label | items |
|---|---|
| context_overflow | 6 |
| ranking_miss | 4 |
| incorrect | 2 |
| missed_refusal | 2 |
| retrieval_miss | 1 |
| unfaithful | 1 |

## Judge failures

No judge parse failures or errors.

## Tokens and cost

Tokens in 76897, tokens out 13816, cost 0.04669650 USD, model calls 82, cache hits 6. Runs stored before T098b count judge cache hits only.

## Tokens and cost per model

This run only. Billed tokens were sent to the provider. Saved tokens were answered by the cache and cost nothing this run. Cost is the list price equivalent of the billed calls.

| model | calls | cached calls | tokens billed | tokens saved | cost billed USD |
|---|---|---|---|---|---|
| openai/gpt-oss-120b | 43 | 0 | 61069 | 0 | 0.014133 |
| qwen/qwen3.8-27b | 39 | 6 | 27636 | 2008 | 0.030419 |

## Latency (non cached calls only)

Milliseconds per item. An item with any cached model call is left out of the generation, judge and total rows, because a cache hit has no real latency. Retrieval is never cached. Retrieval time includes the network round trip to the hosted database.

| stage | items | p50 ms | p95 ms |
|---|---|---|---|
| retrieval | 43 | 938 | 1964 |
| generation | 37 | 2178 | 44612 |
| judge | 38 | 0 | 767 |
| total | 38 | 3899 | 47055 |

## Where answerable items fail

Answerable items that ran: 30. A failed item has one primary label.

| stage | items | labels |
|---|---|---|
| retrieval (gold not in top k) | 5 | ranking_miss 4, retrieval_miss 1 |
| packing (gold in top k, dropped before the prompt) | 6 | context_overflow 6 |
| generation (gold in the prompt) | 3 | incorrect 2, unfaithful 1 |
| pass | 16 |  |

Retrieval and packing together are the stages before the model: 11 of 30.

## Failure label by outcome

An answerable item that abstained is a wrong abstain, listed under its first label.

| label | answered | abstained | refused | error |
|---|---|---|---|---|
| retrieval_miss | 0 | 1 | 0 | 0 |
| ranking_miss | 0 | 4 | 0 | 0 |
| context_overflow | 0 | 6 | 0 | 0 |
| missed_refusal | 1 | 1 | 0 | 0 |
| unfaithful | 1 | 0 | 0 | 0 |
| incorrect | 2 | 0 | 0 | 0 |
| no label (passed) | 16 | 11 | 1 | 0 |

## Worst five answered items

Ranked by the lower of faithfulness and correctness, then by item id.

1. gi-017 (single_fact), label incorrect: correctness 0.50 (1 covered, 1 missing, 0 contradicted), faithfulness 1.00 (3 of 3 claims supported), recall@k 1.00, 5 chunks in the prompt, 1 cited.
2. gi-032 (single_fact), label incorrect: correctness 0.50 (1 covered, 1 missing, 0 contradicted), faithfulness 1.00 (1 of 1 claims supported), recall@k 1.00, 3 chunks in the prompt, 2 cited.
3. gi-044 (multi_chunk), label unfaithful: correctness 1.00 (2 covered, 0 missing, 0 contradicted), faithfulness 0.67 (2 of 3 claims supported), recall@k 1.00, 4 chunks in the prompt, 2 cited.
4. gi-001 (single_fact), label none: correctness 1.00 (4 covered, 0 missing, 0 contradicted), faithfulness 1.00 (4 of 4 claims supported), recall@k 1.00, 5 chunks in the prompt, 1 cited.
5. gi-005 (single_fact), label none: correctness 1.00 (4 covered, 0 missing, 0 contradicted), faithfulness 1.00 (8 of 8 claims supported), recall@k 1.00, 5 chunks in the prompt, 1 cited.

## Not run

- gi-079: not run, needs T122
