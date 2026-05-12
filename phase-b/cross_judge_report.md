# Bonus: Cross-Judge Protocol

This report compares multi-judge agreement and an ensemble winner.

## Setup
- Judge 1: Swap-and-average pairwise winner from Phase B.
- Judge 2: Length-calibrated variant to reduce verbosity bias.
- Judge 3: Proxy from absolute score overall band.
- Ensemble: Majority vote across 3 judges.

## Metrics
- Samples: 40
- Judge1 vs Judge2 agreement: 97.50%
- Ensemble vs Judge1 agreement: 97.50%
- Ensemble vs Judge2 agreement: 100.00%

## Artifact
- `phase-b/cross_judge_results.csv`