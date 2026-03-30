# CWT-CGT Phase 11 Report

## What Phase 11 adds

Phase 11 replaces the effective noisy step with a more explicit **continuous-time Lindblad-style graph-local generator** and checks the mixed-state holonomy lane across the broader benchmark set.

## Benchmark summary at the current coarse switch point (γ ≈ 0.20)

- benchmark_a: trusted pairs = 4, fit R² = None, mean |mixed curvature| = 4.013752287226526e-16
- benchmark_b: trusted pairs = 4, fit R² = None, mean |mixed curvature| = 4.4991844220223677e-10
- benchmark_c: trusted pairs = 4, fit R² = 0.8610126798341613, mean |mixed curvature| = 1.1270578686663146e-05
- benchmark_d: trusted pairs = 4, fit R² = None, mean |mixed curvature| = 9.013434689412744e-06
- benchmark_f: trusted pairs = 0, excluded pairs = 4

## Benchmark C backend comparison

At γ ≈ 0.20:

- mean Bures distance between effective and Lindblad branch densities = 0.0002610504829012277
- metric correlation = 0.9999390020360104
- curvature correlation = 0.9999037435027373
- effective fit = slope 3445.984742447182, R² 0.8152400944967021, count 4
- Lindblad fit = slope -958.235278245205, R² 0.8610126798341613, count 4

## Interpretation

The broad benchmark picture survives the generator upgrade:

- A and D remain null-like controls;
- B remains weak / patchy;
- C remains the positive mixed-state benchmark;
- F remains dominated by branch-switching exclusions.

The current γ grid is coarse, so the switch point should be read as resolved only to the current grid.
