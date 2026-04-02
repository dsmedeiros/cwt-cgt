# Phase 37 Report

## Summary

Phase 37 replaced the remaining lower-order area-channel weighting in the noisy loop-side predictor with a local superoperator-compactness ratio.

## Benchmark C switch-slice metrics

At \(\gamma = 0.30\):

- Phase 36 held-out new-family \(R^2\): **0.9143**
- Phase 37 held-out new-family \(R^2\): **0.9318**
- Phase 36 held-out combined \(R^2\): **0.9680**
- Phase 37 held-out combined \(R^2\): **0.9743**
- Combined correlation: **0.9893**
- Sign agreement: **1.0**

## Reading

This is a real improvement over Phase 36. The broadened held-out transfer stays strong and the lower-order area weighting is now more local and more generator-side.

## Verdict

`local_superoperator_compactness_supported`
