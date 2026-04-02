# Phase 19 Report

## Summary

Phase 19 aligned the noisy loop-side reporting with the accepted Phase 18 analytic field.

That makes the noisy stack cleaner:
- scan-side and loop-side now reference the same structural object;
- benchmark F remains an explicit exclusion lane;
- benchmark C remains the positive noisy benchmark, but only in a fragmented, family-sensitive way.

## Suite verdicts

| Benchmark | Verdict | Switch global R² | Best patch R² |
|---|---:|---:|---:|
| A | null_like | None | None |
| B | weak_control | None | None |
| C | field_aligned_with_shape_residual | 0.0038 | 0.9279 |
| D | null_like | None | None |
| F | excluded_R4 | None | None |

## Benchmark C details

At switch gamma = 0.30:
- global fit slope/intercept: 39.9723, -0.0002;
- global fit R²: 0.0038;
- global corr: 0.0618;
- sign agreement: 0.25;
- best patch: square|(+0.00,+0.00);
- best patch R²: 0.9279;
- shape residual gap: 0.4795;
- boundary-crossing fit R²: 0.2067;
- same-side fit R²: 0.0243.

The main take-away is that the accepted field now organizes the reporting, but not yet the whole loop-side response law.
