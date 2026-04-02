# Phase 39: Local Superoperator Compactness Normalizer

## Goal
Replace the remaining shared train-mean normalization in the compactness-share rule with a more local superoperator-geometry compactness normalizer, while keeping the same broadened held-out loop-family split fixed.

## New local rule
For each trusted loop row:
- `raw_geometry_compactness_share = share_geometry / local_area_share`
- `local_compactness_normalizer = sqrt(local_tensor_share * local_covariance_share) / sqrt(local_area_share)`
- `local_geometry_compactness_ratio = raw_geometry_compactness_share / local_compactness_normalizer`
- `local_compactness_exponent = 0.8 * local_geometry_compactness_ratio`

This replaces the earlier train-mean normalization of the compactness-share geometry ratio.

## Evaluation
The phase is evaluated on the same benchmark-C broadened held-out split used in Phase 38.
