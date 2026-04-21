---
name: Experiment Report
about: Document results of a simulation run, A/B test, or parameter tuning experiment
title: "[EXPERIMENT] "
labels: experiment
assignees: ''
---

## Experiment Goal

[What hypothesis are you testing?]

## Setup

| Parameter | Value |
|-----------|-------|
| World | arena / warehouse |
| Commit | |
| VLM model | |
| Run count | |
| Duration | |

## Results

| Metric | Baseline | This Run | Delta |
|--------|----------|----------|-------|
| Mission success rate | | | |
| Mean mission duration (s) | | | |
| Stuck abort rate | | | |
| Intervention count/mission | | | |
| VLM latency p50 (ms) | | | |
| VLM latency p95 (ms) | | | |

## Observations

[What did you observe that the metrics don't capture?]

## Conclusion

- [ ] Hypothesis confirmed — proceed with change
- [ ] Hypothesis rejected — revert / try alternative
- [ ] Inconclusive — need more data

## Next Steps

[What to try next, or what to ship]
