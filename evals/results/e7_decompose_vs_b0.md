# e7_decompose against the baseline, dev split

Candidate run 89af9b7b-92bc-492d-82ad-4b6fd0d775af (config e7_decompose), baseline run dfaad803-c59e-466c-8e2e-609471d82cee (config b0). Paired on 44 shared items. Difference is candidate minus baseline, 95 percent bootstrap interval, 2000 resamples, seed 0. A gap whose interval holds zero is no clear difference.

Strict pass on answerable items: baseline 15 of 30, candidate 15 of 30. Gained: none. Lost: none.

Rule for the final config: at least one item more than the baseline on the strict rate (not met) and faithfulness not lowered (not lowered). Dev rule verdict: not kept.

Wrong abstains (answerable items declined): baseline 10, candidate 10. Tokens billed: baseline not recorded, candidate 3186. p95 total latency over non cached items, ms: baseline not recorded, candidate too few non cached items.

## Overall

| metric | items | baseline | candidate | difference | interval | verdict |
|---|---|---|---|---|---|---|
| strict_pass | 30 | 0.50 | 0.50 | +0.000 | [+0.000, +0.000] | no clear difference |
| recall | 30 | 0.84 | 0.84 | +0.000 | [+0.000, +0.000] | no clear difference |
| mrr | 30 | 0.81 | 0.81 | +0.000 | [+0.000, +0.000] | no clear difference |
| faithfulness | 20 | 0.98 | 0.98 | +0.000 | [+0.000, +0.000] | no clear difference |
| correctness | 30 | 0.57 | 0.57 | +0.000 | [+0.000, +0.000] | no clear difference |

## single_fact

| metric | items | baseline | candidate | difference | interval | verdict |
|---|---|---|---|---|---|---|
| strict_pass | 19 | 0.74 | 0.74 | +0.000 | [+0.000, +0.000] | no clear difference |
| recall | 19 | 0.84 | 0.84 | +0.000 | [+0.000, +0.000] | no clear difference |
| mrr | 19 | 0.76 | 0.76 | +0.000 | [+0.000, +0.000] | no clear difference |
| faithfulness | 16 | 1.00 | 1.00 | +0.000 | [+0.000, +0.000] | no clear difference |
| correctness | 19 | 0.79 | 0.79 | +0.000 | [+0.000, +0.000] | no clear difference |

## multi_chunk

| metric | items | baseline | candidate | difference | interval | verdict |
|---|---|---|---|---|---|---|
| strict_pass | 11 | 0.09 | 0.09 | +0.000 | [+0.000, +0.000] | no clear difference |
| recall | 11 | 0.83 | 0.83 | +0.000 | [+0.000, +0.000] | no clear difference |
| mrr | 11 | 0.88 | 0.88 | +0.000 | [+0.000, +0.000] | no clear difference |
| faithfulness | 4 | 0.92 | 0.92 | +0.000 | [+0.000, +0.000] | no clear difference |
| correctness | 11 | 0.18 | 0.18 | +0.000 | [+0.000, +0.000] | no clear difference |

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
