# Phase 25 — Moment-Derived Higher-Order Noisy Transfer

## Goal

Replace the Phase 24 **response-fitted higher-order coefficients** with **generator-moment-derived higher-order coefficients** while keeping the clean rerun loop set and held-out family split fixed.

## Source artifact

- `benchmark_c_phase24_clean_rerun_higher_order.json`

## Construction

The lower-order scaffold remains the accepted Phase 24 baseline model on:
- `m2_gap`
- `m2_gap_boundary`
- `area_magnitude`

The new higher-order coefficients are derived from canonical train-row generator moments:

- `m2_gap_var = -|c_gap^(baseline)| * mean_abs(m2_gap) / mean_abs(m2_gap_var)`
- `m2_gap_boundary_var = +sqrt(|c_boundary^(baseline)| mean_abs(m2_gap_boundary) * |c_area^(baseline)| mean_abs(area)) / mean_abs(m2_gap_boundary_var)`

No held-out response refit is used for these higher-order terms.

## Intended test

Check whether the broadened held-out transfer survives once the higher-order correction is generator-derived instead of response-fitted.
