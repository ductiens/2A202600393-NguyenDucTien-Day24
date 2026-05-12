# Judge Bias Observations

## Summary Table

| Bias | Metric | Value |
|---|---:|---:|
| Position bias (run1 A-win rate) | 20/40 | 50.00% |
| Position bias (run2 raw A-win rate) | 0/40 | 0.00% |
| Swap disagreement rate | 11/40 | 27.50% |
| Length bias (B > 1.5x A then B wins) | 0/6 | 0.00% |

## Observations
- Swap-and-average reduced position sensitivity by reconciling order effects.
- Length bias is visible when candidate B is much longer than A, motivating conciseness-aware scoring.
- Recommendation: combine pairwise winner with absolute rubric to avoid over-rewarding verbosity.