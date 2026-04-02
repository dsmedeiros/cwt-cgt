# Phase 23 — Broader Held-Out Generator Transfer

## Goal

Push the accepted **Phase 22 generator-moment coefficient rule** onto a broader held-out loop-family set without refitting the coefficients to observed responses.

## Setup

Canonical train families remain:
- `square`
- `circle`

Accepted held-out base families from Phase 22 remain:
- `diamond`
- `rounded_square`

This phase adds two genuinely new held-out families:
- `ellipse`
- `stadium`

The generator-moment coefficients are reused directly from the accepted Phase 22 artifact at each dephasing value. The only new computation is the loop evaluation for the new families.

## Switch-slice result for benchmark C

At `γ = 0.30`:

- train `R² ≈ 0.9669`
- held-out base `R² ≈ 0.9349`
- held-out new `R² ≈ 0.7885`
- held-out combined `R² ≈ 0.8886`
- held-out combined correlation `≈ 0.9722`
- held-out combined sign agreement `= 1.0000`

Per-shape held-out `R²` values at the switch slice:
- diamond: `0.9812`
- rounded_square: `0.8983`
- ellipse: `0.6552`
- stadium: `0.8392`

## Interpretation

The generator-moment rule still transfers well once the family set is broadened, but the transfer is **weaker on the new families** than on the original diamond/rounded-square pair. The best concise statement is:

> The current benchmark-C noisy loop correction generalizes beyond the original held-out set, but with measurable shape-family decay.

## Verdict

`broader_generator_generalization_with_decay`
