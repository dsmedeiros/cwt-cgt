# CWT-CGT Phase 15 — Generator-Tangent Field

## Goal

Derive the noisy local field more directly from the open-system generator’s **local tangent transport data**, instead of reconstructing it only from minimal plaquette response fits.

## Method

- Use the Lindblad-style graph-local generator at the noisy switch point.
- On each trusted cell, compute the ordered transport mismatch `u→v` vs `v→u`.
- Project that mismatch onto the chosen observable to get a local transport-order gap.
- Divide by the local mixed-curvature area to form a raw ratio.
- Compress with a signed-log transform.
- Remove the benchmark-level median to isolate the structural component.
- Smooth the result into a **centered tangent field**.

## Why this matters

This turns the noisy lane into a two-layer story:

1. an empirical local field (Phase 14), and
2. a generator-derived structural predictor (Phase 15).

## Main result

For benchmark C at `γ = 0.30`, the centered tangent field has structural amplitude `9.063568785210055` and mean zero crossing `u ≈ -0.039865143568660784`. Against the Phase 14 field on overlapping valid cells it achieves correlation `0.9805868137936634`, affine-fit `R² = 0.9615504993860086`, and sign agreement `1.0`.
