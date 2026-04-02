# Phase 38 — Local Superoperator Compactness Share

Objective:
replace the remaining fixed compactness exponent choice in Phase 37 with a more local superoperator-geometry compactness-share rule while keeping the broadened held-out family split fixed.

## Rule

Use the local share

```text
raw_geometry_compactness_share = share_geometry / local_area_share
```

normalize it by its train mean, then let it modulate the exponent on the inverse variance-alignment ratio.

## Why this is the right next move

The Phase 37 compactness rule still hard-coded the exponent `1/2`.
This phase preserves the same loop-side scaffold but localizes that exponent with superoperator geometry.
