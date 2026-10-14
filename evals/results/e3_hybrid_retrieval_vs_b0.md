# e3_hybrid_retrieval_only against the baseline, dev split

Candidate run 6ba747df-c6a2-452b-b62c-fa5ce6b736f6 (config e3_hybrid), baseline run 532b63f3-a706-46f8-b548-43d145e4d15c (config b0). Paired on 44 shared items. Difference is candidate minus baseline, 95 percent bootstrap interval, 2000 resamples, seed 0. A gap whose interval holds zero is no clear difference.

Strict pass on answerable items: baseline 0 of 30, candidate 0 of 30. Gained: none. Lost: none.

Rule for the final config: at least one item more than the baseline on the strict rate (not met) and faithfulness not lowered (not lowered). Result: not kept.

Wrong abstains (answerable items declined): baseline 0, candidate 0. Tokens billed: baseline 0, candidate 0. p95 total latency over non cached items, ms: baseline 7965, candidate 5837.

## Overall

| metric | items | baseline | candidate | difference | interval | verdict |
|---|---|---|---|---|---|---|
| strict_pass | 30 | 0.00 | 0.00 | +0.000 | [+0.000, +0.000] | no clear difference |
| recall | 30 | 0.84 | 0.82 | -0.017 | [-0.150, +0.117] | no clear difference |
| mrr | 30 | 0.81 | 0.67 | -0.138 | [-0.288, +0.017] | no clear difference |
| faithfulness | 0 | n/a | n/a | n/a | n/a | n/a |
| correctness | 0 | n/a | n/a | n/a | n/a | n/a |

## single_fact

| metric | items | baseline | candidate | difference | interval | verdict |
|---|---|---|---|---|---|---|
| strict_pass | 19 | 0.00 | 0.00 | +0.000 | [+0.000, +0.000] | no clear difference |
| recall | 19 | 0.84 | 0.84 | +0.000 | [-0.211, +0.211] | no clear difference |
| mrr | 19 | 0.76 | 0.67 | -0.095 | [-0.314, +0.105] | no clear difference |
| faithfulness | 0 | n/a | n/a | n/a | n/a | n/a |
| correctness | 0 | n/a | n/a | n/a | n/a | n/a |

## multi_chunk

| metric | items | baseline | candidate | difference | interval | verdict |
|---|---|---|---|---|---|---|
| strict_pass | 11 | 0.00 | 0.00 | +0.000 | [+0.000, +0.000] | no clear difference |
| recall | 11 | 0.83 | 0.79 | -0.045 | [-0.136, +0.000] | no clear difference |
| mrr | 11 | 0.88 | 0.67 | -0.212 | [-0.364, -0.061] | candidate is worse |
| faithfulness | 0 | n/a | n/a | n/a | n/a | n/a |
| correctness | 0 | n/a | n/a | n/a | n/a | n/a |

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
