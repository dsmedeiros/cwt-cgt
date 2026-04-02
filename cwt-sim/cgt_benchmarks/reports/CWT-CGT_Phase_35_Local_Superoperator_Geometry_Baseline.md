# Phase 35 — Local Superoperator Geometry Baseline

## Goal

Replace the remaining lower-order baseline ratio in the Phase 34 noisy loop-side predictor with a more local superoperator-geometry rule, while keeping the broadened held-out family split fixed.

## Source artifact

`03_benchmarks/results/benchmark_C_ring/benchmark_c_phase34_local_superoperator_moment_width.json`

## Change introduced

The old baseline ratio used only the geometric mean of local tensor share and local covariance share.  
Phase 35 replaces that with:

\[
B_{\mathrm{geom}}
=
\sqrt{\frac{s_T}{\bar s_T}\frac{s_C}{\bar s_C}}
\cdot
\frac{a}{\bar a}
\cdot
\frac{1}{1 + |\delta_v - \bar\delta_v|},
\]

where:

- \(s_T\) is local tensor share,
- \(s_C\) is local covariance share,
- \(a\) is local area share,
- \(\delta_v\) is local variance deviation.

This raw baseline is then clipped by the existing Phase 34 local moment width.

## Why this matters

This step removes one more lower-order heuristic.  
The baseline scale now depends on a richer local geometry object rather than only a tensor/covariance share product.
