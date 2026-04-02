# CWT-CGT Phase 11 — Continuous-Time Lindblad Upgrade

## Goal

Replace the effective K-step noisy branch map with a more explicit continuous-time graph-local generator and check whether the mixed-state holonomy lane survives across the benchmark set.

## What was implemented

- a new `lindblad.py` module with a local generator built from the branch Hamiltonian, graph-local edge-jump operators, site dephasing, and depolarizing relaxation;
- a new `phase11_analysis.py` layer that evaluates the mixed-state scan/loop observables under that generator;
- per-benchmark Phase 11 payloads for A, B, C, D, and F;
- a direct effective-vs-Lindblad comparison on benchmark C.

## Why this matters

This is the first pass where the noisy lane is not just a discrete effective branch map. The mixed-state geometry is now checked against a continuous-time noisy construction that uses the same local graph ingredients in generator form.

## Boundary of the claim

This phase does **not** claim a final microscopic derivation of the noisy law. It claims that the mixed-state benchmark picture is stable under a stronger noisy implementation.
