# CWT-CGT Phase 29 — Local Superoperator Area Share

## Goal

Replace the remaining symmetry-average area compactness share from Phase 28 with a more local superoperator-geometry derivation while keeping the broadened held-out family set unchanged.

## Accepted construction

For canonical train rows:
- compute `boundary_compactness`,
- compute `boundary_transport_compactness`,
- compute `area_compactness`,
- compute `mean_abs_generator_var`.

Then define
- `eta_local = 0.5 * ((1 - boundary_compactness) + (area_compactness - boundary_transport_compactness))`.

For each loop row `i`, define
- `local_variance_ratio_i = |generator_var_mean_i| / mean_abs_generator_var`,
- `local_area_share_i = clip(1 + eta_local * (local_variance_ratio_i - 1), 0.75, 1.25)`.

Use that share only on the area term of the accepted noisy-loop predictor.

## Interpretation

This phase does not change the benchmark split, the broadened held-out families, or the higher-order rule. It only localizes the remaining coarse area-side choice.
