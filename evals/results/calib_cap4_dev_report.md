# Eval report, run 80c1977c-a2fb-4792-91cc-c2c44b775a2a

Config calib_cap4, split dev, mode full. Items run: 44. Items not run: 1.

Intervals are 95 percent bootstrap intervals of the mean, 2000 resamples, seed 0. Items that share a source document are resampled together. A cell shows n when some items had no value for it.

Headline: 19 of 30 answerable items pass strictly (faithfulness 1.0 and correctness 1.0), rate 0.63 [0.47, 0.80]. The overall pass rate is 0.70 [0.57, 0.84] over 44 items.

Unanswerable items pass by abstaining, so they raise the overall pass rate. The headline leaves them out.

## Results per category

| category | items | pass rate | recall@k | hit | MRR | context precision | citation precision | citation recall | faithfulness | correctness |
|---|---|---|---|---|---|---|---|---|---|---|
| single_fact | 19 | 0.74 [0.53, 0.95] | 0.84 [0.68, 1.00] | 0.84 [0.68, 1.00] | 0.76 [0.58, 0.92] | 0.18 [0.14, 0.22] | 0.77 [0.59, 0.93] (n=17) | 0.79 [0.58, 0.95] | 1.00 [1.00, 1.00] (n=17) | 0.82 [0.66, 0.95] |
| multi_chunk | 11 | 0.45 [0.18, 0.73] | 0.83 [0.70, 0.95] | 1.00 [1.00, 1.00] | 0.88 [0.70, 1.00] | 0.38 [0.33, 0.44] | 0.80 [0.58, 1.00] (n=7) | 0.55 [0.27, 0.82] | 0.95 [0.86, 1.00] (n=7) | 0.55 [0.27, 0.82] |
| unanswerable | 11 | 1.00 [1.00, 1.00] | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| adversarial | 3 | 0.33 [0.00, 1.00] | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| all | 44 | 0.70 [0.57, 0.84] | 0.84 [0.72, 0.94] (n=30) | 0.90 [0.80, 1.00] (n=30) | 0.81 [0.68, 0.92] (n=30) | 0.25 [0.21, 0.30] (n=30) | 0.78 [0.63, 0.91] (n=24) | 0.70 [0.53, 0.85] (n=30) | 0.99 [0.96, 1.00] (n=24) | 0.72 [0.55, 0.87] (n=30) |

## Abstain and refusal

| cell | items |
|---|---|
| correct abstain | 11 |
| wrong abstain | 6 |
| missed abstain | 0 |
| correct refusal | 1 |
| wrong refusal | 0 |
| missed refusal | 2 |
| system errors | 0 |

## Failure labels

| label | items |
|---|---|
| ranking_miss | 5 |
| missed_refusal | 2 |
| retrieval_miss | 2 |
| context_distraction | 1 |
| context_overflow | 1 |
| incorrect | 1 |
| unfaithful | 1 |

## Judge failures

No judge parse failures or errors.

## Tokens and cost

Tokens in 82486, tokens out 14408, cost 0.05381365 USD, model calls 91, cache hits 39. Runs stored before T098b count judge cache hits only.

## Tokens and cost per model

This run only. Billed tokens were sent to the provider. Saved tokens were answered by the cache and cost nothing this run. Cost is the list price equivalent of the billed calls.

| model | calls | cached calls | tokens billed | tokens saved | cost billed USD |
|---|---|---|---|---|---|
| openai/gpt-oss-120b | 43 | 17 | 37668 | 23498 | 0.009004 |
| qwen/qwen3.8-27b | 48 | 22 | 21707 | 14021 | 0.024511 |

## Where answerable items fail

Answerable items that ran: 30. A failed item has one primary label.

| stage | items | labels |
|---|---|---|
| retrieval (gold not in top k) | 7 | ranking_miss 5, retrieval_miss 2 |
| packing (gold in top k, dropped before the prompt) | 1 | context_overflow 1 |
| generation (gold in the prompt) | 3 | context_distraction 1, incorrect 1, unfaithful 1 |
| pass | 19 |  |

Retrieval and packing together are the stages before the model: 8 of 30.

## Failure label by outcome

An answerable item that abstained is a wrong abstain, listed under its first label.

| label | answered | abstained | refused | error |
|---|---|---|---|---|
| retrieval_miss | 1 | 1 | 0 | 0 |
| ranking_miss | 1 | 4 | 0 | 0 |
| context_overflow | 0 | 1 | 0 | 0 |
| context_distraction | 1 | 0 | 0 | 0 |
| missed_refusal | 0 | 2 | 0 | 0 |
| unfaithful | 1 | 0 | 0 | 0 |
| incorrect | 1 | 0 | 0 | 0 |
| no label (passed) | 19 | 11 | 1 | 0 |

## Worst five answered items

Ranked by the lower of faithfulness and correctness, then by item id.

1. gi-047 (multi_chunk), label retrieval_miss: correctness 0.00 (0 covered, 2 missing, 0 contradicted), faithfulness 1.00 (14 of 14 claims supported), recall@k 0.50, 5 chunks in the prompt, 4 cited.
2. gi-008 (single_fact), label ranking_miss: correctness 0.50 (1 covered, 1 missing, 0 contradicted), faithfulness 1.00 (1 of 1 claims supported), recall@k 0.00, 4 chunks in the prompt, 3 cited.
3. gi-017 (single_fact), label incorrect: correctness 0.50 (1 covered, 1 missing, 0 contradicted), faithfulness 1.00 (3 of 3 claims supported), recall@k 1.00, 5 chunks in the prompt, 1 cited.
4. gi-032 (single_fact), label context_distraction: correctness 0.50 (1 covered, 1 missing, 0 contradicted), faithfulness 1.00 (1 of 1 claims supported), recall@k 1.00, 4 chunks in the prompt, 1 cited.
5. gi-044 (multi_chunk), label unfaithful: correctness 1.00 (2 covered, 0 missing, 0 contradicted), faithfulness 0.67 (2 of 3 claims supported), recall@k 1.00, 4 chunks in the prompt, 2 cited.

## Not run

- gi-079: not run, needs T122
