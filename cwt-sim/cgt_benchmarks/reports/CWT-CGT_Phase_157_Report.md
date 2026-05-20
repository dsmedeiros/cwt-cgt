# Phase 157 Report — Ninth Bridge Benchmark AC

Added **benchmark AC (hidden-dropout batching)** as a ninth bridge-style benchmark.

Switch slice `γ = 0.30`:
- held-out combined `R² ≈ 0.9238`
- combined correlation `≈ 0.9824`
- sign agreement `= 1.0`

Interpretation: AC supports the existing pooled-eight bridge predictor despite a harsher observation bottleneck.
