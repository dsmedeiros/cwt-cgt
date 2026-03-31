# CWT-CGT Theory / Implementation Alignment — v13

## Alignment status

The implementation now matches the accepted v14 noisy-lane language.

## What is implemented

- The empirical noisy object from Phase 14 remains the **smoothed local mixed-state field** built from minimal plaquettes of the Lindblad-style generator.
- Phase 15 adds a **generator-derived centered tangent field** built from local transport-order commutators:
  - lower-left density `ρ00`,
  - ordered transports `u→v` and `v→u`,
  - observable transport gap `Tr[O(ρ_uv - ρ_vu)]`,
  - local mixed-curvature area from the same cell,
  - signed-log compression,
  - benchmark-level median removal,
  - Gaussian smoothing with `sqrt(|curvature area|)` weights.
- The accepted benchmark-C tangent comparison is now structural rather than absolute-unit quantitative. The code reports overlap correlation, affine-fit R², sign agreement, and zero-crossing alignment.

## What is deliberately not implemented as a final claim

- No claim that the centered tangent field alone replaces the empirical Phase 14 field.
- No claim that the current generator is a final derivation from the nonlinear graph update rule.
- No claim that secondary observables inherit the same strong noisy sign boundary.

## Practical consequence

The implementation now supports a narrower but better-earned theory statement: the positive noisy benchmark has both an empirical local field and a generator-side structural predictor, and those agree strongly on benchmark C.
