# Abstain threshold trade-off, B0 dev split

Analysis only (T102a). No code path reads a threshold other than 0.0.

## Decision

The B0 abstain threshold stays 0.0 (owner decision). It is not tuned into B0. A threshold becomes a technique of Phase 5, compared with B0 by a paired comparison on the same items.

## What the B0 dev rows show

- The generator already abstained on 11 of 11 unanswerable dev items. A threshold would only save those generator calls, not add a correct abstain.
- Top-1 dense score of the 30 answerable items starts at 0.557 (median 0.725). Unanswerable items go up to 0.629 (median 0.511).
- The ranges overlap: 4 answerable items score at or below the highest unanswerable score, and 3 unanswerable items score at or above the lowest answerable score.
- B0 abstained on 10 of 30 answerable items already (wrong abstain by the generator).

## Table

Rule: abstain before generation when the best score is below the threshold (a score equal to the threshold is kept). Calls saved counts every dev item below the threshold that reached the generator in the stored B0 run; items refused by policy are not counted.

| threshold | answerable wrongly abstained | of which B0 had answered | unanswerable abstained before generation | generator calls saved |
|---|---|---|---|---|
| 0.40 | 0 | 0 | 2 | 2 |
| 0.41 | 0 | 0 | 2 | 2 |
| 0.42 | 0 | 0 | 2 | 2 |
| 0.43 | 0 | 0 | 2 | 2 |
| 0.44 | 0 | 0 | 3 | 3 |
| 0.45 | 0 | 0 | 3 | 4 |
| 0.46 | 0 | 0 | 4 | 5 |
| 0.47 | 0 | 0 | 5 | 6 |
| 0.48 | 0 | 0 | 5 | 6 |
| 0.49 | 0 | 0 | 5 | 6 |
| 0.50 | 0 | 0 | 5 | 6 |
| 0.51 | 0 | 0 | 5 | 6 |
| 0.52 | 0 | 0 | 6 | 7 |
| 0.53 | 0 | 0 | 7 | 8 |
| 0.54 | 0 | 0 | 7 | 8 |
| 0.55 | 0 | 0 | 8 | 9 |
| 0.56 | 1 | 1 | 8 | 10 |
| 0.57 | 1 | 1 | 8 | 10 |
| 0.58 | 2 | 2 | 9 | 12 |
| 0.59 | 3 | 3 | 10 | 14 |
| 0.60 | 3 | 3 | 10 | 14 |
| 0.61 | 3 | 3 | 10 | 14 |
| 0.62 | 3 | 3 | 10 | 14 |
| 0.63 | 4 | 4 | 11 | 16 |
| 0.64 | 5 | 4 | 11 | 18 |
| 0.65 | 5 | 4 | 11 | 18 |
| 0.66 | 7 | 6 | 11 | 20 |
| 0.67 | 7 | 6 | 11 | 20 |
| 0.68 | 8 | 7 | 11 | 21 |
| 0.69 | 12 | 10 | 11 | 25 |
| 0.70 | 12 | 10 | 11 | 25 |

Source: top-1 scores from re-running B0 retrieval on the dev split (dense, no model call) and outcomes from the stored B0 full dev run. Per item data is in the json file.
