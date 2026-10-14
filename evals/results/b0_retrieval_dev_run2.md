# Eval report, run 9fc1fbda-b7d8-4db5-af63-495ce20a02d4

Config b0, split dev, mode retrieval_only. Items run: 44. Items not run: 1.

Intervals are 95 percent bootstrap intervals of the mean, 2000 resamples, seed 0. Items that share a source document are resampled together. A cell shows n when some items had no value for it.

Headline: 0 of 30 answerable items pass strictly (faithfulness 1.0 and correctness 1.0), rate 0.00 [0.00, 0.00]. The overall pass rate is n/a over 44 items.

Unanswerable items pass by abstaining, so they raise the overall pass rate. The headline leaves them out.

## Results per category

| category | items | pass rate | recall@k | hit | MRR | context precision | citation precision | citation recall | faithfulness | correctness |
|---|---|---|---|---|---|---|---|---|---|---|
| single_fact | 19 | n/a | 0.84 [0.68, 1.00] | 0.84 [0.68, 1.00] | 0.76 [0.58, 0.92] | 0.18 [0.14, 0.22] | n/a | n/a | n/a | n/a |
| multi_chunk | 11 | n/a | 0.83 [0.70, 0.95] | 1.00 (all values equal) | 0.88 [0.70, 1.00] | 0.38 [0.33, 0.44] | n/a | n/a | n/a | n/a |
| unanswerable | 11 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| adversarial | 3 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| all | 44 | n/a | 0.84 [0.72, 0.94] (n=30) | 0.90 [0.80, 1.00] (n=30) | 0.81 [0.68, 0.92] (n=30) | 0.25 [0.21, 0.30] (n=30) | n/a | n/a | n/a | n/a |

## Abstain and refusal

| cell | items |
|---|---|
| correct abstain | 0 |
| wrong abstain | 0 |
| missed abstain | 0 |
| correct refusal | 0 |
| wrong refusal | 0 |
| missed refusal | 0 |
| system errors | 0 |

Abstention precision is the share of right abstains among abstains on items that are not refusal items. Abstention recall is the share of abstain items that abstained. The interval resamples items.

| rate | items | value |
|---|---|---|
| abstention precision | 0 | n/a |
| abstention recall | 11 | 0.00 (all values equal) |

## Failure labels

No failed items.

## Judge failures

No judge parse failures or errors.

## Tokens and cost

Tokens in 0, tokens out 0, cost 0 USD, model calls 0, cache hits 0. Runs stored before T098b count judge cache hits only.

## Tokens and cost per model

The per run token numbers are not available for this run: it was stored before per call usage was recorded, and the cache folder cannot say which run a call belonged to.

## Latency

Latency: not recorded for this run (it was stored before per item timings existed, and old runs are not backfilled).

## Where answerable items fail

Answerable items that ran: 30. A failed item has one primary label.

| stage | items | labels |
|---|---|---|
| retrieval (gold not in top k) | 0 |  |
| packing (gold in top k, dropped before the prompt) | 0 |  |
| generation (gold in the prompt) | 0 |  |
| pass | 30 |  |

Retrieval and packing together are the stages before the model: 0 of 30.

## Failure label by outcome

An answerable item that abstained is a wrong abstain, listed under its first label.

| label | answered | abstained | refused | error |
|---|---|---|---|---|
| no label (passed) | 0 | 0 | 0 | 0 |

## Not run

- gi-079: not run, needs T122
