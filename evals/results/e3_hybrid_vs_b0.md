# e3_hybrid against the baseline, dev split

Candidate run b509fe25-240f-4ecd-8aa5-753d0eca22ca (config e3_hybrid), baseline run dfaad803-c59e-466c-8e2e-609471d82cee (config b0). Paired on 44 shared items. Difference is candidate minus baseline, 95 percent bootstrap interval, 2000 resamples, seed 0. A gap whose interval holds zero is no clear difference.

Strict pass on answerable items: baseline 15 of 30, candidate 16 of 30. Gained: gi-008, gi-014, gi-024, gi-047. Lost: gi-003, gi-016, gi-026.

Rule for the final config: at least one item more than the baseline on the strict rate (met) and faithfulness not lowered (not lowered). Dev rule verdict: kept.

Wrong abstains (answerable items declined): baseline 10, candidate 11. Tokens billed: baseline not recorded, candidate 88705. p95 total latency over non cached items, ms: baseline not recorded, candidate 47055.

## Overall

| metric | items | baseline | candidate | difference | interval | verdict |
|---|---|---|---|---|---|---|
| strict_pass | 30 | 0.50 | 0.53 | +0.033 | [-0.133, +0.200] | no clear difference |
| recall | 30 | 0.84 | 0.82 | -0.017 | [-0.150, +0.117] | no clear difference |
| mrr | 30 | 0.81 | 0.67 | -0.138 | [-0.288, +0.017] | no clear difference |
| faithfulness | 16 | 0.98 | 0.98 | +0.000 | [+0.000, +0.000] | no clear difference |
| correctness | 30 | 0.57 | 0.60 | +0.033 | [-0.133, +0.200] | no clear difference |

## single_fact

| metric | items | baseline | candidate | difference | interval | verdict |
|---|---|---|---|---|---|---|
| strict_pass | 19 | 0.74 | 0.74 | +0.000 | [-0.263, +0.263] | no clear difference |
| recall | 19 | 0.84 | 0.84 | +0.000 | [-0.211, +0.211] | no clear difference |
| mrr | 19 | 0.76 | 0.67 | -0.095 | [-0.314, +0.105] | no clear difference |
| faithfulness | 13 | 1.00 | 1.00 | +0.000 | [+0.000, +0.000] | no clear difference |
| correctness | 19 | 0.79 | 0.79 | +0.000 | [-0.263, +0.263] | no clear difference |

## multi_chunk

| metric | items | baseline | candidate | difference | interval | verdict |
|---|---|---|---|---|---|---|
| strict_pass | 11 | 0.09 | 0.18 | +0.091 | [+0.000, +0.273] | no clear difference |
| recall | 11 | 0.83 | 0.79 | -0.045 | [-0.136, +0.000] | no clear difference |
| mrr | 11 | 0.88 | 0.67 | -0.212 | [-0.364, -0.061] | candidate is worse |
| faithfulness | 3 | 0.89 | 0.89 | +0.000 | [+0.000, +0.000] | no clear difference |
| correctness | 11 | 0.18 | 0.27 | +0.091 | [+0.000, +0.273] | no clear difference |

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
