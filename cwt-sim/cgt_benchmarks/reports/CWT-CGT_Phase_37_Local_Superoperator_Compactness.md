# Phase 37 — Local Superoperator Compactness

## Goal

Replace the remaining lower-order area-channel weighting from Phase 36 with a more local superoperator-geometry compactness rule while keeping the broadened held-out family split fixed.

## Source artifact

`03_benchmarks/results/benchmark_C_ring/benchmark_c_phase36_local_superoperator_area_channel.json`

## Change introduced

Phase 36 used the lower-order area factor

\[
c_{\mathrm{area}}\, A_{\mathrm{loc}}\, |A|,
\]

with \(A_{\mathrm{loc}}\) built from local share geometry and local area share.

Phase 37 multiplies that area channel by

\[
C_{\mathrm{loc}} =
\frac{(\bar v_{\mathrm{align}} / v_{\mathrm{align}})^{1/2}}
     {\overline{(\bar v_{\mathrm{align}} / v_{\mathrm{align}})^{1/2}}},
\]

so the final lower-order area channel becomes

\[
A_{\mathrm{compact}} = A_{\mathrm{loc}} C_{\mathrm{loc}}.
\]

## Why this matters

This removes another residual pragmatic weighting and ties the remaining lower-order shape sensitivity to a local compactness rule derived from superoperator-side variance alignment.
