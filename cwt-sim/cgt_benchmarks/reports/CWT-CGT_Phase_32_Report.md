# Phase 32 Report

## Outcome

Benchmark C remains the positive noisy benchmark, and the accepted loop-side rule is now slightly more generator-derived than in Phase 31.

### Switch slice (\(\gamma=0.30\))

- Held-out new-family \(R^2\): **0.9091**
- Held-out combined \(R^2\): **0.9672**
- Combined correlation: **0.9868**
- Sign agreement: **1.0**

### Verdicts

- benchmark A: `null_like`
- benchmark B: `weak_control`
- benchmark C: `covariance_tensor_baseline_supported`
- benchmark D: `null_like`
- benchmark F: `excluded_R4`

## Interpretation

Phase 32 shows that the remaining local baseline modulation can be expressed through generator-side covariance/tensor share moments instead of staying as a free baseline constant. The improvement is small, which is what we should expect at this stage: the theory is now being tightened more than transformed.
