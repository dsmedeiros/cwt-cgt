# Phase 19 — Loop-Side Alignment to the Phase 18 Analytic Field

## Goal

Use the accepted Phase 18 analytic scan-side field as the reference structural object for noisy loop-side reporting.

## Method

For each noisy loop-family record from Phase 13:
1. read the aligned mixed holonomy gap;
2. sample the Phase 18 analytic field over the loop footprint;
3. form a structural loop predictor from the loop-footprint field average times the aligned mixed holonomy gap;
4. compare observed orientation gap against that predictor globally, by patch, by shape, by center, and by boundary-crossing class.

## Benchmark C outcome at switch

- global fit: weak, R² ≈ 0.0038;
- best patch: square|(+0.00,+0.00), R² ≈ 0.9279;
- shape residual gap: ≈ 0.4795.

## Interpretation

This step succeeds as a harmonization step but not as a complete closure step.
The loop-side noisy story is now tied to the accepted scan-side field, but benchmark C still shows a strong family residual that the current scalar field alone does not absorb.
