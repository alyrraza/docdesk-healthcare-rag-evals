# Eval report, run f4a588e4-1eee-40ee-b183-2a27fc0727ec

Config e4_title_drop, split dev, mode full. Items run: 44. Items not run: 1.

Intervals are 95 percent bootstrap intervals of the mean, 2000 resamples, seed 0. Items that share a source document are resampled together. A cell shows n when some items had no value for it.

Headline: 15 of 30 answerable items pass strictly (faithfulness 1.0 and correctness 1.0), rate 0.50 [0.33, 0.70]. The overall pass rate is 0.61 [0.48, 0.75] over 44 items.

Unanswerable items pass by abstaining, so they raise the overall pass rate. The headline leaves them out.

## Results per category

| category | items | pass rate | recall@k | hit | MRR | context precision | citation precision | citation recall | faithfulness | correctness |
|---|---|---|---|---|---|---|---|---|---|---|
| single_fact | 19 | 0.74 [0.53, 0.95] | 0.95 [0.84, 1.00] | 0.95 [0.84, 1.00] | 0.78 [0.63, 0.93] | 0.20 [0.17, 0.23] | 0.88 [0.72, 1.00] (n=16) | 0.79 [0.58, 0.95] | 1.00 (all values equal) (n=16) | 0.79 [0.61, 0.95] |
| multi_chunk | 11 | 0.09 [0.00, 0.27] | 0.83 [0.70, 0.95] | 1.00 (all values equal) | 0.88 [0.70, 1.00] | 0.38 [0.33, 0.44] | 0.58 [0.17, 1.00] (n=4) | 0.23 [0.00, 0.45] | 0.92 [0.75, 1.00] (n=4) | 0.18 [0.00, 0.45] |
| unanswerable | 11 | 1.00 (all values equal) | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| adversarial | 3 | 0.33 [0.00, 1.00] | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| all | 44 | 0.61 [0.48, 0.75] | 0.91 [0.82, 0.98] (n=30) | 0.97 [0.90, 1.00] (n=30) | 0.82 [0.70, 0.92] (n=30) | 0.27 [0.23, 0.31] (n=30) | 0.82 [0.66, 0.95] (n=20) | 0.58 [0.40, 0.75] (n=30) | 0.98 [0.95, 1.00] (n=20) | 0.57 [0.38, 0.73] (n=30) |

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

Abstention precision is the share of right abstains among abstains on items that are not refusal items. Abstention recall is the share of abstain items that abstained. The interval resamples items.

| rate | items | value |
|---|---|---|
| abstention precision | 21 | 0.52 [0.33, 0.71] |
| abstention recall | 11 | 1.00 (all values equal) |

## Failure labels

| label | items |
|---|---|
| context_overflow | 7 |
| ranking_miss | 3 |
| missed_refusal | 2 |
| retrieval_miss | 2 |
| context_distraction | 1 |
| incorrect | 1 |
| unfaithful | 1 |

## Judge failures

No judge parse failures or errors.

## Tokens and cost

Tokens in 66899, tokens out 12815, cost 0.04246145 USD, model calls 83, cache hits 74. Runs stored before T098b count judge cache hits only.

## Tokens and cost per model

This run only. Billed tokens were sent to the provider. Saved tokens were answered by the cache and cost nothing this run. Cost is the list price equivalent of the billed calls.

| model | calls | cached calls | tokens billed | tokens saved | cost billed USD |
|---|---|---|---|---|---|
| openai/gpt-oss-120b | 43 | 37 | 6443 | 46962 | 0.001455 |
| qwen/qwen3.8-27b | 40 | 37 | 1992 | 24317 | 0.002163 |

## Latency (non cached calls only)

Milliseconds per item. An item with any cached model call is left out of the generation, judge and total rows, because a cache hit has no real latency. Retrieval is never cached. Retrieval time includes the network round trip to the hosted database.

| stage | items | p50 ms | p95 ms |
|---|---|---|---|
| retrieval | 43 | 669 | 1591 |
| generation | 3 | 1083 | 1589 |
| total | 4 | 1874 | 2594 |

## Where answerable items fail

Answerable items that ran: 30. A failed item has one primary label.

| stage | items | labels |
|---|---|---|
| retrieval (gold not in top k) | 5 | ranking_miss 3, retrieval_miss 2 |
| packing (gold in top k, dropped before the prompt) | 7 | context_overflow 7 |
| generation (gold in the prompt) | 3 | context_distraction 1, incorrect 1, unfaithful 1 |
| pass | 15 |  |

Retrieval and packing together are the stages before the model: 12 of 30.

## Failure label by outcome

An answerable item that abstained is a wrong abstain, listed under its first label.

| label | answered | abstained | refused | error |
|---|---|---|---|---|
| retrieval_miss | 1 | 1 | 0 | 0 |
| ranking_miss | 0 | 3 | 0 | 0 |
| context_overflow | 1 | 6 | 0 | 0 |
| context_distraction | 1 | 0 | 0 | 0 |
| missed_refusal | 0 | 2 | 0 | 0 |
| unfaithful | 1 | 0 | 0 | 0 |
| incorrect | 1 | 0 | 0 | 0 |
| no label (passed) | 15 | 11 | 1 | 0 |

## Worst five answered items

Ranked by the lower of faithfulness and correctness, then by item id.

1. gi-039 (multi_chunk), label context_overflow: correctness 0.00 (0 covered, 2 missing, 0 contradicted), faithfulness 1.00 (3 of 3 claims supported), recall@k 1.00, 2 chunks in the prompt, 1 cited.
2. gi-047 (multi_chunk), label retrieval_miss: correctness 0.00 (0 covered, 2 missing, 0 contradicted), faithfulness 1.00 (13 of 13 claims supported), recall@k 0.50, 3 chunks in the prompt, 3 cited.
3. gi-017 (single_fact), label incorrect: correctness 0.50 (1 covered, 1 missing, 0 contradicted), faithfulness 1.00 (3 of 3 claims supported), recall@k 1.00, 5 chunks in the prompt, 1 cited.
4. gi-032 (single_fact), label context_distraction: correctness 0.50 (1 covered, 1 missing, 0 contradicted), faithfulness 1.00 (1 of 1 claims supported), recall@k 1.00, 2 chunks in the prompt, 1 cited.
5. gi-044 (multi_chunk), label unfaithful: correctness 1.00 (2 covered, 0 missing, 0 contradicted), faithfulness 0.67 (2 of 3 claims supported), recall@k 1.00, 4 chunks in the prompt, 2 cited.

## Not run

- gi-079: not run, needs T122
