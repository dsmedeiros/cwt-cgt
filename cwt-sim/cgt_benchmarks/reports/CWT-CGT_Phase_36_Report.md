# Phase 36 Report

## Summary

Phase 36 replaced the remaining lower-order area proxy in the noisy loop-side predictor with a local superoperator-geometry area channel.

## Benchmark C switch-slice metrics

At \(\gamma = 0.30\):

- Phase 35 held-out new-family \(R^2\): **0.9110**
- Phase 36 held-out new-family \(R^2\): **0.9143**
- Phase 35 held-out combined \(R^2\): **0.9679**
- Phase 36 held-out combined \(R^2\): **0.9680**
- Combined correlation: **0.9883**
- Sign agreement: **1.0**

## Reading

This is a modest but real improvement over Phase 35. The broadened held-out transfer survives and the lower-order area term is now more local and more generator-side.

## Verdict

`local_superoperator_area_channel_supported`
