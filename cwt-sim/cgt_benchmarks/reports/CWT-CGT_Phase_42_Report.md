# Phase 42 Report

## Summary
Phase 42 adds **benchmark H** as a third positive noisy scaffold benchmark and evaluates the pooled positive-noisy scaffold rule from Phase 41 unchanged.

## Switch slice (`γ = 0.30`)
- train `R² ≈ 0.9648`
- held-out base `R² ≈ 0.9761`
- held-out new `R² ≈ 0.9604`
- held-out combined `R² ≈ 0.9667`
- combined correlation `≈ 0.9986`
- sign agreement `= 1.0`

## Three-benchmark pooled view at switch
Using held-out rows from C, G, and H under the same pooled rule:
- pooled held-out combined `R² ≈ 0.9520`
- pooled held-out combined correlation `≈ 0.9880`
- sign agreement `= 1.0`
- held-out row count = 105

## Interpretation
This strengthens the noisy scaffold lane from a shared two-benchmark rule to a shared **three-benchmark scaffold rule**. It is still scaffold validation, not external validation.
