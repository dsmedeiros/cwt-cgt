
# CWT-CGT Theory Hardened v70

This version updates the bridge lane after phases 218–226.

## Main updates

- Added a strict expanded benchmark-holdout comparison of the **minimal bridge rule** versus **tensor-law v6** on the bridge + pilot set.
- Added a ninth less-synthetic pilot, **II_partial_obs_spike**.
- Built **bridge tensor geometry law v7** from expanded holdout localization and pilot-aware adjustment.
- Compared **v7** against **v6** on the same expanded holdout split.
- Built pooled **bridge + pilot** positive and adversarial summaries.
- Stopped further internal bridge-only tuning once gains became small and localized.

## Current bridge lane interpretation

The bridge lane still supports a shared correction structure, but the gains from successive tensor-law refinements are now small. The most valuable progress now comes from **externalization pressure** rather than further synthetic compression.

## Current switch-slice bridge lane summary (`γ = 0.30`)

- strict holdout mean, minimal: `R² ≈ 0.8804`
- strict holdout mean, tensor-law v6: `R² ≈ 0.9006`
- strict holdout mean, tensor-law v7: `R² ≈ 0.9031`
- pooled-thirteen bridge adversarial corrected under v7: `R² ≈ 0.9212`
- bridge positive mean vs pilot positive mean gap: `≈ 0.0378`
- bridge adversarial corrected mean vs pilot adversarial corrected mean gap: `≈ 0.0709`

## Current verdict

The coherent/passive branch-resolved core remains the strongest part of the theory. The noisy scaffold layer remains stronger than the bridge / pilot lane. The bridge lane is now broad enough to support a **disciplined externalization program**, but not yet broad enough to claim that the bridge correction is final.
