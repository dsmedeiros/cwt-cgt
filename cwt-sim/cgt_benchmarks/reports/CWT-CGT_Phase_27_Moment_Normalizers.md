# CWT-CGT Phase 27 — Moment Normalizers

## Aim

Replace the remaining fixed lower-order structural normalizers in the broadened held-out noisy-loop transfer model with **generator-moment normalizers**, then rerun the exact same held-out family set unchanged.

## Inputs kept fixed

- same broadened held-out dataset as Phase 24 / Phase 26,
- same canonical train families,
- same held-out base and held-out new families,
- same response rows and no new response refit.

## New lower-order normalizers

Given canonical train-row generator moments:
- `mean_abs(m2_gap)`
- `mean_abs(m2_gap_boundary)`
- `mean_abs(area)`
- `mean_signed(m2_gap)`

we define:
- `gap_share_normalizer = mean_abs(m2_gap_boundary) / (2 * (mean_abs(m2_gap_boundary) + mean_signed(m2_gap)))`
- `boundary_geometric_normalizer = sqrt(mean_abs(m2_gap_boundary) / mean_abs(m2_gap)) + polarization`
- `area_structure_normalizer = boundary_ratio - polarization / 2`

These replace the older fixed constants that were carried through Phase 26.

## Result at γ = 0.30

- Phase 26 held-out new-family `R² ≈ 0.8673`
- Phase 27 held-out new-family `R² ≈ 0.8691`
- Phase 26 held-out combined `R² ≈ 0.9249`
- Phase 27 held-out combined `R² ≈ 0.9254`

## Verdict

`moment_normalizer_transfer_supported`
