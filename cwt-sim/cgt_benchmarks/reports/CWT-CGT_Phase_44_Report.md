# Phase 44 Report

## Summary
Phase 44 keeps the pooled positive-noisy scaffold rule fixed and adds a **stronger perturbation family** on benchmark I.

## Switch slice (`γ = 0.30`)
- held-out base `R² ≈ 0.9800`
- held-out new `R² ≈ 0.9701`
- held-out strong `R² ≈ 0.8836`
- held-out combined `R² ≈ 0.9403`
- combined correlation `≈ 0.9933`
- sign agreement `= 1.0`

## Interpretation
The stronger perturbation family adds value because it stresses the same non-ring benchmark more aggressively without changing the pooled rule. Performance decays relative to the base held-out set but remains strong enough to support the noisy scaffold layer within the program.
