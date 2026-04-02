# Phase 23 Report

## Summary

This phase extends the held-out family transfer test beyond `diamond` and `rounded_square` by adding `ellipse` and `stadium` loops while keeping the **Phase 22 generator-moment coefficients fixed**.

## Main benchmark-C result

At the switch slice `γ = 0.30`:

- train fit: `R² = 0.9669`
- held-out base fit: `R² = 0.9349`
- held-out new-family fit: `R² = 0.7885`
- held-out combined fit: `R² = 0.8886`
- held-out combined correlation: `0.9722`
- held-out combined sign agreement: `1.0000`

## Readout

The old held-out pair remains very strong, while the new families are weaker but still clearly structured. This means the noisy loop-side correction is no longer supported only on one narrow held-out pair. It survives a broader family extension, but not without decay.

## Accepted suite verdicts

- benchmark A: null_like (inherited)
- benchmark B: weak_control (inherited)
- benchmark C: broader_generator_generalization_with_decay
- benchmark D: null_like (inherited)
- benchmark F: excluded_R4 (inherited)
