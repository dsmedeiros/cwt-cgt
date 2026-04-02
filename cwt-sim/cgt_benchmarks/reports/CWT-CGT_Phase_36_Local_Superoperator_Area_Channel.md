# Phase 36 — Local Superoperator Geometry Area Channel

## Goal

Replace the remaining lower-order area proxy from Phase 35 with a more local superoperator-geometry area channel while keeping the broadened held-out family split fixed.

## Source artifact

`03_benchmarks/results/benchmark_C_ring/benchmark_c_phase35_local_superoperator_geometry_baseline.json`

## Change introduced

Phase 35 used the lower-order area factor

\[
c_{\mathrm{area}}\, s_C \, |A|,
\]

with \(s_C\) acting as the area proxy.

Phase 36 replaces that proxy by

\[
A_{\mathrm{loc}} =
\left(\frac{s_\mathrm{geom}}{\bar s_\mathrm{geom}}\right)
\left(\frac{a}{\bar a}\right)^{1/4},
\]

where:

- \(s_\mathrm{geom}\) is local share geometry,
- \(a\) is local area share,
- bars denote train-side means.

The quarter-power keeps area influence sublinear, which matches the observation that the residual was shape-sensitive but not dominated by raw area alone.

## Why this matters

This removes one more pragmatic proxy from the lower-order noisy term and moves the loop-side area response closer to a local generator-geometry rule.
