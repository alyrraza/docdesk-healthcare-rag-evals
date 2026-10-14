# final against the baseline, dev split

Candidate run 07e3ffbb-89fa-45b6-895f-0908d6862657 (config final_simple), baseline run dfaad803-c59e-466c-8e2e-609471d82cee (config b0). Paired on 44 shared items. Difference is candidate minus baseline, 95 percent bootstrap interval, 2000 resamples, seed 0. A gap whose interval holds zero is no clear difference.

Strict pass on answerable items: baseline 15 of 30, candidate 19 of 30. Gained: gi-035, gi-039, gi-041, gi-042. Lost: none.

Rule for the final config: at least one item more than the baseline on the strict rate (met) and faithfulness not lowered (not lowered). Result: kept.

Wrong abstains (answerable items declined): baseline 10, candidate 6. Tokens billed: baseline not recorded, candidate 0. p95 total latency over non cached items, ms: baseline not recorded, candidate too few non cached items.

## Overall

| metric | items | baseline | candidate | difference | interval | verdict |
|---|---|---|---|---|---|---|
| strict_pass | 30 | 0.50 | 0.63 | +0.133 | [+0.033, +0.267] | candidate is better |
| recall | 30 | 0.84 | 0.84 | +0.000 | [+0.000, +0.000] | no clear difference |
| mrr | 30 | 0.81 | 0.81 | +0.000 | [+0.000, +0.000] | no clear difference |
| faithfulness | 20 | 0.98 | 0.98 | +0.000 | [+0.000, +0.000] | no clear difference |
| correctness | 30 | 0.57 | 0.72 | +0.150 | [+0.033, +0.267] | candidate is better |

## single_fact

| metric | items | baseline | candidate | difference | interval | verdict |
|---|---|---|---|---|---|---|
| strict_pass | 19 | 0.74 | 0.74 | +0.000 | [+0.000, +0.000] | no clear difference |
| recall | 19 | 0.84 | 0.84 | +0.000 | [+0.000, +0.000] | no clear difference |
| mrr | 19 | 0.76 | 0.76 | +0.000 | [+0.000, +0.000] | no clear difference |
| faithfulness | 16 | 1.00 | 1.00 | +0.000 | [+0.000, +0.000] | no clear difference |
| correctness | 19 | 0.79 | 0.82 | +0.026 | [+0.000, +0.079] | no clear difference |

## multi_chunk

| metric | items | baseline | candidate | difference | interval | verdict |
|---|---|---|---|---|---|---|
| strict_pass | 11 | 0.09 | 0.45 | +0.364 | [+0.091, +0.636] | candidate is better |
| recall | 11 | 0.83 | 0.83 | +0.000 | [+0.000, +0.000] | no clear difference |
| mrr | 11 | 0.88 | 0.88 | +0.000 | [+0.000, +0.000] | no clear difference |
| faithfulness | 4 | 0.92 | 0.92 | +0.000 | [+0.000, +0.000] | no clear difference |
| correctness | 11 | 0.18 | 0.55 | +0.364 | [+0.091, +0.636] | candidate is better |

## unanswerable

| metric | items | baseline | candidate | difference | interval | verdict |
|---|---|---|---|---|---|---|
| strict_pass | 0 | n/a | n/a | n/a | n/a | n/a |
| recall | 0 | n/a | n/a | n/a | n/a | n/a |
| mrr | 0 | n/a | n/a | n/a | n/a | n/a |
| faithfulness | 0 | n/a | n/a | n/a | n/a | n/a |
| correctness | 0 | n/a | n/a | n/a | n/a | n/a |

## adversarial

| metric | items | baseline | candidate | difference | interval | verdict |
|---|---|---|---|---|---|---|
| strict_pass | 0 | n/a | n/a | n/a | n/a | n/a |
| recall | 0 | n/a | n/a | n/a | n/a | n/a |
| mrr | 0 | n/a | n/a | n/a | n/a | n/a |
| faithfulness | 0 | n/a | n/a | n/a | n/a | n/a |
| correctness | 0 | n/a | n/a | n/a | n/a | n/a |

## Not completed

- FINAL_FULL (cap 4 plus hybrid): not completed, the daily generator token budget was spent (168122 of 170000). No run exists.
- top_k 8 (run 22fb6b60): not completed, stopped by the same budget. Retrieval only recall at 8 is 0.93, not comparable with recall at 5.
