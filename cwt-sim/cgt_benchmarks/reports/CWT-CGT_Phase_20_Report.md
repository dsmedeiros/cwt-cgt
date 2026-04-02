# Phase 20 Report

## Summary

Phase 20 introduced a boundary-aware generator path-order correction for the noisy loop-side layer.
The scan-side reference object stays fixed: the Phase 18 analytic field.
The new ingredient is a second-Magnus correction from the linear Lindblad superoperator, with an additional modulation by signed distance to the accepted sign boundary.

## Suite verdicts

- benchmark A: null_like
- benchmark B: weak_control
- benchmark C: path_order_corrected
- benchmark D: null_like
- benchmark F: excluded_R4

## Benchmark C switch result

At γ = 0.30:
- field-only R² ≈ 0.0038
- corrected R² ≈ 0.9566
- field-only corr ≈ 0.0617
- corrected corr ≈ 0.9874
- sign agreement = 1.0000
- shape residual gap = 0.4806 → 0.0481
- square-group R² = 0.2646 → 0.8742
- circle-group R² = 0.7451 → 0.9223

## Benchmark C dephasing trend

- γ = 0.00: field-only R² ≈ 0.0037, corrected R² ≈ 0.9626
- γ = 0.10: field-only R² ≈ 0.0037, corrected R² ≈ 0.9737
- γ = 0.20: field-only R² ≈ 0.0038, corrected R² ≈ 0.9727
- γ = 0.30: field-only R² ≈ 0.0038, corrected R² ≈ 0.9566

## Why benchmark D is not promoted

Benchmark D is still kept as null_like.
The noisy loop-side correction is not accepted there because the scan-side structural gate is not passed and the benchmark does not provide the same multi-shape closure test that benchmark C does.
