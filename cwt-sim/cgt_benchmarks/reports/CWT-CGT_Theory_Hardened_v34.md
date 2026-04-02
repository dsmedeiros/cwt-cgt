# CWT-CGT Theory — Hardened v34

## Current form

The theory remains a layered, benchmarked framework:

1. **Coherent passive core**: branch-resolved, regime-labeled, geometry-blind readout, no invalid global phase kick.
2. **Switching lane**: explicit R4 branch-switching benchmark and exclusions.
3. **Topology lane**: restricted to the auxiliary periodic/gapped sector only.
4. **Noisy lane**: local structural field + generator-derived loop-side corrections.

## Phase 35 update

Phase 35 replaces the remaining lower-order baseline ratio in the Phase 34 noisy loop-side rule with a **local superoperator-geometry baseline** built from:

- local tensor share,
- local covariance share,
- local area share,
- and local variance-alignment relative to the train-set generator moments.

The broadened held-out family set is unchanged.

At the benchmark-C switch slice \(\gamma = 0.30\):

- Phase 34 held-out new-family fit: **0.9101**
- Phase 35 held-out new-family fit: **0.9110**
- Phase 34 held-out combined fit: **0.9674**
- Phase 35 held-out combined fit: **0.9679**
- Combined correlation: **0.9871**
- Sign agreement: **1.0**

## Current benchmark reading

- A: null-like control
- B: weak control / partial structure
- C: positive benchmark with broadened held-out transfer still intact
- D: null-like control
- F: explicit exclusion / branch-switching benchmark

## What this means

This is another derivational tightening step. The held-out metrics improve slightly, and the remaining lower-order noisy baseline now depends more directly on local generator-side geometry than on a simpler tensor/covariance-only share.

## Boundary of the current claim

This still does **not** justify a shape-universal noisy law. The noisy benchmark remains strongest on benchmark C, and the loop-side transfer still depends on benchmark-specific structural objects even though more of them are now generator-derived.
