# test_split_b0_vs_final against the baseline, test split

Candidate run 6e8a809d-34b3-41c4-8ca5-56eb634d0134 (config final), baseline run 40488aff-a8dd-4605-a009-a1e9d674edfc (config b0). Paired on 29 shared items. Difference is candidate minus baseline, 95 percent bootstrap interval, 2000 resamples, seed 0. A gap whose interval holds zero is no clear difference.

Strict pass on answerable items: baseline 13 of 20, candidate 15 of 20. Gained: gi-038, gi-040, gi-054. Lost: gi-045.

Wrong abstains (answerable items declined): baseline 5, candidate 3. Tokens billed: baseline 54019, candidate 39030. p95 total latency over non cached items, ms: baseline 41609, candidate 44030.

## Overall

| metric | items | baseline | candidate | difference | interval | verdict |
|---|---|---|---|---|---|---|
| strict_pass | 20 | 0.65 | 0.75 | +0.100 | [-0.100, +0.300] | no clear difference |
| recall | 20 | 0.85 | 0.85 | +0.000 | [+0.000, +0.000] | no clear difference |
| mrr | 20 | 0.83 | 0.83 | +0.000 | [+0.000, +0.000] | no clear difference |
| faithfulness | 15 | 0.99 | 1.00 | +0.006 | [+0.000, +0.018] | no clear difference |
| correctness | 20 | 0.70 | 0.78 | +0.075 | [-0.100, +0.250] | no clear difference |

## single_fact

| metric | items | baseline | candidate | difference | interval | verdict |
|---|---|---|---|---|---|---|
| strict_pass | 12 | 1.00 | 1.00 | +0.000 | [+0.000, +0.000] | no clear difference |
| recall | 12 | 1.00 | 1.00 | +0.000 | [+0.000, +0.000] | no clear difference |
| mrr | 12 | 0.90 | 0.90 | +0.000 | [+0.000, +0.000] | no clear difference |
| faithfulness | 12 | 1.00 | 1.00 | +0.000 | [+0.000, +0.000] | no clear difference |
| correctness | 12 | 1.00 | 1.00 | +0.000 | [+0.000, +0.000] | no clear difference |

## multi_chunk

| metric | items | baseline | candidate | difference | interval | verdict |
|---|---|---|---|---|---|---|
| strict_pass | 8 | 0.12 | 0.38 | +0.250 | [-0.250, +0.625] | no clear difference |
| recall | 8 | 0.62 | 0.62 | +0.000 | [+0.000, +0.000] | no clear difference |
| mrr | 8 | 0.71 | 0.71 | +0.000 | [+0.000, +0.000] | no clear difference |
| faithfulness | 3 | 0.97 | 1.00 | +0.030 | [+0.000, +0.091] | no clear difference |
| correctness | 8 | 0.25 | 0.44 | +0.188 | [-0.250, +0.562] | no clear difference |

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

- Injected adversarial items: not run (they need the fixture loader, T122).
