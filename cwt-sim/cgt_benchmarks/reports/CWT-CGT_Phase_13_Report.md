# CWT-CGT Phase 13 Report

## What Phase 13 adds

Phase 13 replaces the noisy lane’s single global slope with a **local mixed-state susceptibility atlas** estimated from the continuous-time Lindblad-style graph-local generator.

Each benchmark is now summarized by patch families (shape × center), with per-patch slope, fit quality, trusted/excluded counts, and a locality gap against the global fit at the recommended mixed-state switch γ.

## Suite summary at the recommended switch γ

- benchmark_a: verdict=null_like, switch γ=0.30, global R²=None, best patch=None, best patch R²=None, locality gap=None, trusted=6, excluded=0
- benchmark_b: verdict=weak_control, switch γ=0.30, global R²=None, best patch=None, best patch R²=None, locality gap=None, trusted=6, excluded=6
- benchmark_c: verdict=local_fragmented, switch γ=0.30, global R²=0.06176010627482531, best patch=square|(+0.00,+0.00), best patch R²=0.8751907407006734, locality gap=0.8134306344258481, trusted=12, excluded=0
- benchmark_d: verdict=null_like, switch γ=0.30, global R²=None, best patch=None, best patch R²=None, locality gap=None, trusted=4, excluded=0
- benchmark_f: verdict=excluded_R4, switch γ=0.30, global R²=None, best patch=None, best patch R²=None, locality gap=None, trusted=0, excluded=6

## Per-benchmark patch-family summaries

### benchmark_a

- Verdict: null_like
- Switch γ: 0.30
- Global slope / R²: None / None
- Best patch: None (R²=None)
- Trusted / excluded pairs: 6 / 0

| patch | class | slope | R² | trusted | excluded | side lengths |
|---|---:|---:|---:|---:|---:|---|
| square|(+0.00,+0.00) | insufficient | None | None | 3 | 0 | 0.10, 0.16, 0.22 |
| circle|(+0.00,+0.00) | insufficient | None | None | 3 | 0 | 0.10, 0.16, 0.22 |

Patch slope plot: `/mnt/data/CWT-CGT_Project/05_reports/plots/phase13_local_atlas/benchmark_A_dimer/patch_slope_at_switch.png`
Patch R² plot: `/mnt/data/CWT-CGT_Project/05_reports/plots/phase13_local_atlas/benchmark_A_dimer/patch_r2_at_switch.png`

### benchmark_b

- Verdict: weak_control
- Switch γ: 0.30
- Global slope / R²: None / None
- Best patch: None (R²=None)
- Trusted / excluded pairs: 6 / 6

| patch | class | slope | R² | trusted | excluded | side lengths |
|---|---:|---:|---:|---:|---:|---|
| square|(+0.00,+0.00) | insufficient | None | None | 3 | 0 | 0.10, 0.16, 0.22 |
| square|(+0.00,+0.20) | insufficient | None | None | 0 | 3 | 0.10, 0.16, 0.22 |
| circle|(+0.00,+0.00) | insufficient | None | None | 3 | 0 | 0.10, 0.16, 0.22 |
| circle|(+0.00,+0.20) | insufficient | None | None | 0 | 3 | 0.10, 0.16, 0.22 |

Patch slope plot: `/mnt/data/CWT-CGT_Project/05_reports/plots/phase13_local_atlas/benchmark_B_line/patch_slope_at_switch.png`
Patch R² plot: `/mnt/data/CWT-CGT_Project/05_reports/plots/phase13_local_atlas/benchmark_B_line/patch_r2_at_switch.png`

### benchmark_c

- Verdict: local_fragmented
- Switch γ: 0.30
- Global slope / R²: -1203.536797117855 / 0.06176010627482531
- Best patch: square|(+0.00,+0.00) (R²=0.8751907407006734)
- Trusted / excluded pairs: 12 / 0

| patch | class | slope | R² | trusted | excluded | side lengths |
|---|---:|---:|---:|---:|---:|---|
| square|(+0.00,+0.00) | negative | -1231.2282481368431 | 0.8751907407006734 | 3 | 0 | 0.10, 0.16, 0.22 |
| square|(+0.18,+0.00) | positive | 1281.2837115166344 | 0.6104153799451988 | 3 | 0 | 0.10, 0.16, 0.22 |
| circle|(+0.00,+0.00) | negative | -5649.79175590957 | 0.8644422872239274 | 3 | 0 | 0.10, 0.16, 0.22 |
| circle|(+0.18,+0.00) | negative | -10471.390201076663 | 0.7567150259588884 | 3 | 0 | 0.10, 0.16, 0.22 |

Patch slope plot: `/mnt/data/CWT-CGT_Project/05_reports/plots/phase13_local_atlas/benchmark_C_ring/patch_slope_at_switch.png`
Patch R² plot: `/mnt/data/CWT-CGT_Project/05_reports/plots/phase13_local_atlas/benchmark_C_ring/patch_r2_at_switch.png`
Patch slope vs dephasing: `/mnt/data/CWT-CGT_Project/05_reports/plots/phase13_local_atlas/benchmark_C_ring/patch_slope_vs_dephasing.png`
Patch R² vs dephasing: `/mnt/data/CWT-CGT_Project/05_reports/plots/phase13_local_atlas/benchmark_C_ring/patch_r2_vs_dephasing.png`

### benchmark_d

- Verdict: null_like
- Switch γ: 0.30
- Global slope / R²: None / None
- Best patch: None (R²=None)
- Trusted / excluded pairs: 4 / 0

| patch | class | slope | R² | trusted | excluded | side lengths |
|---|---:|---:|---:|---:|---:|---|
| square|(+0.00,+0.23) | insufficient | None | None | 2 | 0 | 0.04, 0.06 |
| square|(+0.03,+0.23) | insufficient | None | None | 2 | 0 | 0.04, 0.06 |

Patch slope plot: `/mnt/data/CWT-CGT_Project/05_reports/plots/phase13_local_atlas/benchmark_D_random_walk/patch_slope_at_switch.png`
Patch R² plot: `/mnt/data/CWT-CGT_Project/05_reports/plots/phase13_local_atlas/benchmark_D_random_walk/patch_r2_at_switch.png`

### benchmark_f

- Verdict: excluded_R4
- Switch γ: 0.30
- Global slope / R²: None / None
- Best patch: None (R²=None)
- Trusted / excluded pairs: 0 / 6

| patch | class | slope | R² | trusted | excluded | side lengths |
|---|---:|---:|---:|---:|---:|---|
| square|(+0.00,+0.00) | insufficient | None | None | 0 | 2 | 0.18, 0.30 |
| square|(+0.70,+0.00) | insufficient | None | None | 0 | 2 | 0.18, 0.30 |
| square|(-0.70,+0.00) | insufficient | None | None | 0 | 2 | 0.18, 0.30 |

Patch slope plot: `/mnt/data/CWT-CGT_Project/05_reports/plots/phase13_local_atlas/benchmark_F_bistable_line/patch_slope_at_switch.png`
Patch R² plot: `/mnt/data/CWT-CGT_Project/05_reports/plots/phase13_local_atlas/benchmark_F_bistable_line/patch_r2_at_switch.png`

## Interpretation

- The noisy response law is now best treated as **local** in patch family rather than as one benchmark-wide coefficient.
- Benchmark C remains the positive mixed-state benchmark, but only as a patchwise atlas claim.
- Benchmarks A and D remain null-like controls in this lane.
- Benchmark B is weak / patchy rather than robustly positive.
- Benchmark F remains an exclusion benchmark dominated by branch ambiguity / switching.

Suite plot: `/mnt/data/CWT-CGT_Project/05_reports/plots/phase13_local_atlas/suite_global_vs_local_r2.png`