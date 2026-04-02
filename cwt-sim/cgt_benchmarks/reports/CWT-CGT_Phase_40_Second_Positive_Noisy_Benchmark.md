# Phase 40 — Second Positive Noisy Scaffold Benchmark

Goal: stop refining benchmark C alone and ask whether the accepted noisy loop-side rule survives on a second genuinely non-null benchmark under the same held-out family split.

## Design
Benchmark G is a designed four-node skew-ring-style scaffold benchmark.
It keeps the same shape split:
- train: square, circle
- held-out base: diamond, rounded_square
- held-out new: ellipse, stadium, hexagon

The accepted Phase 39 rule from benchmark C is reused unchanged.

## Boundary
This is a scaffold generalization test, not an external validation benchmark.
