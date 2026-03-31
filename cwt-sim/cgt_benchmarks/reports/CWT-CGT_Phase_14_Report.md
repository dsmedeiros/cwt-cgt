# CWT-CGT Phase 14 Report

## What Phase 14 adds

Phase 14 replaces the discrete patch-family noisy atlas with a **smoothed local mixed-state field** built from generator-driven minimal plaquettes.

Each benchmark is now summarized by:
- trusted vs excluded minimal plaquettes,
- valid local-field cells after a holonomy floor and effective-support filter,
- local sign-consistency and sign-boundary structure,
- sampled field values at the Phase 13 by-center reference points when available.

## Suite summary at the recommended switch γ

- benchmark_a: verdict=null_like, switch γ=0.30, valid field cells=0, trusted plaquettes=36, excluded plaquettes=0, zero-crossing u=None
- benchmark_b: verdict=weak_control, switch γ=0.30, valid field cells=0, trusted plaquettes=18, excluded plaquettes=18, zero-crossing u=None
- benchmark_c: verdict=structured_sign_boundary, switch γ=0.30, valid field cells=25, trusted plaquettes=18, excluded plaquettes=18, zero-crossing u=-0.027546077265929093
- benchmark_d: verdict=null_like, switch γ=0.30, valid field cells=0, trusted plaquettes=36, excluded plaquettes=0, zero-crossing u=None
- benchmark_f: verdict=excluded_R4, switch γ=0.30, valid field cells=0, trusted plaquettes=0, excluded plaquettes=36, zero-crossing u=None

## Focus benchmark interpretation

Focus benchmark: **benchmark_c** at switch γ=0.30.
The smoothed field has 25 valid cells and 5 zero-crossing samples.
Mean field consistency on valid cells: 0.7231184415424835.
Mean zero-crossing location in control-1: -0.027546077265929093.

| center | sampled χ | consistency | effective support | mean abs holonomy gap |
|---|---:|---:|---:|---:|
| (+0.00,+0.00) | 12.678970992943233 | 0.5070664205122907 | 3.6397218415137416 | 2.249908224090676e-07 |
| (+0.18,+0.00) | 126.76713000472692 | 0.8953616037068242 | 3.8418498226706475 | 3.1738668836993414e-07 |

## Interpretation

- Benchmarks A and D remain null-like at the noisy switch point under the local-field filter.
- Benchmark B remains weak: it does not clear the local-field holonomy floor at the switch point.
- Benchmark C remains the positive noisy benchmark, but it is now described as a **structured local field with a sign boundary**, not just a discrete patch table.
- Benchmark F remains an exclusion / R4 benchmark with no trusted local-field cells.

Suite plot: `/mnt/data/CWT-CGT_Project/05_reports/plots/phase14_local_field/suite_valid_field_cells.png`
