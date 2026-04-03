# Phase 41 — Pooled Positive Noisy Scaffold Rule

Goal: move beyond one-way transfer and test whether benchmarks C and G support a **shared scaffold-level noisy rule**.

## Design
- benchmark C source: Phase 39 positive noisy rule rows
- benchmark G source: Phase 40 second positive noisy scaffold rows
- train rows: `square`, `circle` from **both** benchmarks pooled together
- held-out base: `diamond`, `rounded_square`
- held-out new: benchmark-specific new shapes left untouched

## Boundary
This is still a scaffold-only result. The pooled rule is stronger than one-way transfer, but it is not external empirical validation.
