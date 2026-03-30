# CWT-CGT Phase 9 Report

## Scope

Phase 9 completes the next strengthening step proposed at the end of v7:

1. add a fuller operational noisy/CPTP lane;
2. add direct branch-jump observables.

## Main outcomes

### Ring benchmark noisy lane

The current noisy benchmark payload reports:

- recommended mixed-state switch dephasing γ ≈ 0.30
- baseline global orientation-gap fit R² ≈ 0.312782
- patchwise baseline fits ranging from about R² = 0.736218 to R² = 0.956682
- switch-point patchwise fits ranging from about R² = 0.691283 to R² = 0.936452

Interpretation: the noisy law is still patchwise stronger than global, which is consistent with the trusted-patch reading already adopted in the coherent theory.

### Bistable benchmark branch-jump lane

The explicit branch-jump payload reports:

- switch tiles = 35
- ambiguous tiles = 35
- trusted loop pairs = 4
- excluded loop pairs = 5
- maximum total switch count in a loop pair = 2.000000

Interpretation: the code now measures branch switching directly and uses it to justify loop exclusion explicitly.

## What changed in the project tree

Phase 9 adds new code, plots, reports, and updated theory notes. The bundle now contains:

- a coherent scan/loop path for benchmarks A–D and F,
- an operational noisy/CPTP lane for benchmark C,
- a branch-jump report for benchmark F,
- updated theory documents aligned to the live implementation.

## Limitation carried forward

The noisy lane is explicit and operational, but still not yet the final microscopic theory. Uhlmann curvature and graph-derived open-system generators remain later work.
