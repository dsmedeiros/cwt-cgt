# Phase 25 Report

## Summary

Phase 25 keeps the Phase 24 clean rerun dataset fixed and replaces the higher-order noisy-loop correction coefficients with generator-moment rules.

## Switch-slice result on benchmark C (γ = 0.30)

- baseline held-out new-family `R² ≈ 0.7937`
- moment-derived held-out new-family `R² ≈ 0.8459`
- baseline held-out combined `R² ≈ 0.8862`
- moment-derived held-out combined `R² ≈ 0.9286`
- moment-derived held-out combined correlation `≈ 0.9661`
- moment-derived held-out combined sign agreement `= 1.0`

## Interpretation

This is a strengthening step because the higher-order improvement survives even after removing direct response fitting from those higher-order terms.

It is also an honesty step because the report makes the boundary clear:
- the higher-order correction is now generator-derived,
- but the lower-order scaffold is still inherited from Phase 24.

## Verdict

`moment_derived_higher_order_supported`
