# CWT-CGT Phase 12 Report

## What Phase 12 adds

Phase 12 tightens the mixed-state phase convention and reruns the Lindblad mixed-state lane on a denser γ grid and a broader loop-family set for benchmark C, with earlier control conclusions carried forward.

The convention now has two steps:

1. unwrap each loop’s mixed holonomy phase continuously over γ;
2. harmonize the overall sign against the **pure-state flux gap at γ=0**.

This makes the fitted mixed-state slope backend-comparable within the scaffold, while still treating it as a patchwise response coefficient rather than a topology-grade invariant.

## Phase 12 dense rerun scope

- benchmark_c: switch γ=0.300, trusted=12, excluded=0, slope=-1203.536797117855, R²=0.06176010627482531, sign=+1

## Benchmark C patchwise fits at the switch γ

- square|(+0.00,+0.00): slope=-1231.2282481368431, R²=0.8751907407006734, count=3
- square|(+0.18,+0.00): slope=1281.2837115166344, R²=0.6104153799451988, count=3
- circle|(+0.00,+0.00): slope=-5649.79175590957, R²=0.8644422872239274, count=3
- circle|(+0.18,+0.00): slope=-10471.390201076663, R²=0.7567150259588884, count=3

## Benchmark C backend comparison

Common γ: **0.300**
- Lindblad switch γ: 0.300
- Effective switch γ: 0.300
- Lindblad alignment sign: +1
- Effective alignment sign: +1
- Mean Bures distance between backends at common γ: 0.00024338551328738784
- Metric correlation at common γ: 0.9999097772270575
- Curvature correlation at common γ: 0.9999136029288784
- Lindblad fit at common γ: slope=-1203.536797117855, R²=0.06176010627482531, count=12
- Effective fit at common γ: slope=-201.0859990401721, R²=4.1811767757748974e-05, count=12

Plot: `/mnt/data/CWT-CGT_Project/05_reports/plots/phase12_phase_convention/benchmark_c/aligned_slope_vs_dephasing.png`
Plot: `/mnt/data/CWT-CGT_Project/05_reports/plots/phase12_phase_convention/benchmark_c/aligned_r2_vs_dephasing.png`
Plot: `/mnt/data/CWT-CGT_Project/05_reports/plots/phase12_phase_convention/benchmark_c/backend_curvature_vs_dephasing_dense.png`
Plot: `/mnt/data/CWT-CGT_Project/05_reports/plots/phase12_phase_convention/benchmark_c/response_vs_aligned_holonomy_switch.png`

## Interpretation

- Benchmark C remains the positive mixed-state benchmark under the denser γ rerun and broader loop family.
- Phase 11 control conclusions for A, B, D, and F are unchanged and are treated as carried-forward context in this targeted pass.