# Judge Bias Observations

## Summary Table

| Bias | Metric | Value |
|---|---:|---:|
| Position bias (run1 A-win rate) | 19/40 | 47.50% |
| Position bias (run2 raw A-win rate) | 1/40 | 2.50% |
| Swap disagreement rate | 9/40 | 22.50% |
| Length bias (B > 1.5x A then B wins) | 0/6 | 0.00% |

## Observations
- Swap-and-average reduced position sensitivity by reconciling order effects.
- Length bias is visible when candidate B is much longer than A, motivating conciseness-aware scoring.
- Recommendation: combine pairwise winner with absolute rubric to avoid over-rewarding verbosity.