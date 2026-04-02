# CWT-CGT Theory Hardened v37

## Increment in this phase

Phase 38 replaces the remaining fixed compactness exponent in the lower-order noisy loop-side compactness channel with a **local superoperator-geometry compactness-share rule**.

The accepted local compactness share is

```text
raw_geometry_compactness_share = share_geometry / local_area_share
local_geometry_compactness_share = raw_geometry_compactness_share / mean_train(raw_geometry_compactness_share)
local_compactness_exponent = 0.5 * local_geometry_compactness_share
local_compactness_ratio = ((mean_train(variance_alignment) / variance_alignment) ** local_compactness_exponent) / mean_train(raw_compactness_ratio)
```

and the loop-side predictor keeps the same lower- and higher-order structure as Phase 37 while replacing only the fixed exponent choice.

## Current accepted noisy loop-side claim

For the current benchmark-C broadened held-out split, the noisy loop-side predictor is best understood as a branch-resolved local structural law in which:

- the lower-order gap and boundary-gap channels are retained,
- the area channel is modulated by a local compactness ratio,
- and that compactness ratio is now driven by local superoperator geometry rather than by a globally fixed exponent.

## Switch-slice result

At the switch slice `γ = 0.30`:

- Phase 37 held-out new-family `R² ≈ 0.9318`
- Phase 38 held-out new-family `R² ≈ 0.9321`
- Phase 37 held-out combined `R² ≈ 0.9743`
- Phase 38 held-out combined `R² ≈ 0.9744`
- combined correlation `≈ 0.9893`
- sign agreement `= 1.0`

## Current suite verdict

- A: `null_like`
- B: `weak_control`
- C: `local_superoperator_compactness_share_supported`
- D: `null_like`
- F: `excluded_R4`
