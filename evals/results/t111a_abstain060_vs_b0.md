# t111a_abstain060 against the baseline, dev split

Candidate run d0c644b8-1818-4f79-9f4a-1b54cc6f82c4 (config t111a_abstain060), baseline run dfaad803-c59e-466c-8e2e-609471d82cee (config b0). Paired on 44 shared items. Difference is candidate minus baseline, 95 percent bootstrap interval, 2000 resamples, seed 0. A gap whose interval holds zero is no clear difference.

Strict pass on answerable items: baseline 15 of 30, candidate 13 of 30. Gained: none. Lost: gi-021, gi-034.

Rule for the final config: at least one item more than the baseline on the strict rate (not met) and faithfulness not lowered (not lowered). Result: not kept.

Wrong abstains (answerable items declined): baseline 10, candidate 13. Tokens billed: baseline not recorded, candidate 0. p95 total latency over non cached items, ms: baseline not recorded, candidate 910.

## Overall

| metric | items | baseline | candidate | difference | interval | verdict |
|---|---|---|---|---|---|---|
| strict_pass | 30 | 0.50 | 0.43 | -0.067 | [-0.167, +0.000] | no clear difference |
| recall | 30 | 0.84 | 0.84 | +0.000 | [+0.000, +0.000] | no clear difference |
| mrr | 30 | 0.81 | 0.81 | +0.000 | [+0.000, +0.000] | no clear difference |
| faithfulness | 17 | 1.00 | 1.00 | +0.000 | [+0.000, +0.000] | no clear difference |
| correctness | 30 | 0.57 | 0.47 | -0.100 | [-0.200, +0.000] | no clear difference |

## single_fact

| metric | items | baseline | candidate | difference | interval | verdict |
|---|---|---|---|---|---|---|
| strict_pass | 19 | 0.74 | 0.63 | -0.105 | [-0.263, +0.000] | no clear difference |
| recall | 19 | 0.84 | 0.84 | +0.000 | [+0.000, +0.000] | no clear difference |
| mrr | 19 | 0.76 | 0.76 | +0.000 | [+0.000, +0.000] | no clear difference |
| faithfulness | 14 | 1.00 | 1.00 | +0.000 | [+0.000, +0.000] | no clear difference |
| correctness | 19 | 0.79 | 0.68 | -0.105 | [-0.263, +0.000] | no clear difference |

## multi_chunk

| metric | items | baseline | candidate | difference | interval | verdict |
|---|---|---|---|---|---|---|
| strict_pass | 11 | 0.09 | 0.09 | +0.000 | [+0.000, +0.000] | no clear difference |
| recall | 11 | 0.83 | 0.83 | +0.000 | [+0.000, +0.000] | no clear difference |
| mrr | 11 | 0.88 | 0.88 | +0.000 | [+0.000, +0.000] | no clear difference |
| faithfulness | 3 | 1.00 | 1.00 | +0.000 | [+0.000, +0.000] | no clear difference |
| correctness | 11 | 0.18 | 0.09 | -0.091 | [-0.273, +0.000] | no clear difference |

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
