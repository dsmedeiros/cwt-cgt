# Phase 35 Report

## Summary

Phase 35 replaced the remaining lower-order baseline ratio in the noisy loop-side predictor with a local superoperator-geometry baseline.

## Benchmark C switch-slice metrics

At \(\gamma = 0.30\):

- Phase 34 held-out new-family \(R^2\): **0.9101**
- Phase 35 held-out new-family \(R^2\): **0.9110**
- Phase 34 held-out combined \(R^2\): **0.9674**
- Phase 35 held-out combined \(R^2\): **0.9679**
- Combined correlation: **0.9871**
- Sign agreement: **1.0**

## Reading

This is a small but real improvement over Phase 34.  
The broadened held-out transfer survives, and the lower-order scale is now more local and more generator-side.

## Verdict

`local_superoperator_geometry_baseline_supported`
