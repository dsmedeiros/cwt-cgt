# Phase 21 Report

## Summary

Phase 21 tests whether the noisy loop-side correction transfers to held-out loop families.
The scan-side reference object stays fixed: the Phase 18 analytic field.
The loop-side correction is trained only on square/circle families and then evaluated unchanged on diamond/rounded-square families.

## Suite verdicts
- benchmark_a: null_like
- benchmark_b: weak_control
- benchmark_c: heldout_generator_generalized
- benchmark_d: null_like
- benchmark_f: excluded_R4


## Benchmark C switch result

At γ = 0.30:
- canonical train R² ≈ 0.9705
- held-out R² ≈ 0.9492
- held-out corr ≈ 0.9911
- held-out sign agreement = 1.0

Per-shape switch-slice fits:
- square: count = 6, R² ≈ 0.9815, corr ≈ 0.9990
- circle: count = 6, R² ≈ 0.9519, corr ≈ 0.9927
- diamond: count = 6, R² ≈ 0.9917, corr ≈ 0.9985
- rounded_square: count = 6, R² ≈ 0.9187, corr ≈ 0.9918


## Why this matters

Phase 20 showed that a boundary-aware path-order correction could close the square-versus-circle residual in benchmark C.
Phase 21 shows that the same correction structure also transfers to held-out shapes, which is stronger evidence that the noisy loop-side layer is tracking a real generator-side effect rather than just fitting one family.

## Limits

- The transfer coefficients are still calibrated from data, not yet derived analytically.
- The strong transfer result is benchmark-C specific in this pass.
- Benchmarks A and D remain null-like, B stays weak-control, and F stays excluded by explicit branch switching.
