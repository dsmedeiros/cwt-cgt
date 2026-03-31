# CWT-CGT Phase 15 Report

## What Phase 15 adds

Phase 15 derives the noisy local field more directly from **generator tangent transport data** rather than reconstructing it only from minimal-plaquette response fits.

The accepted tangent object is the **centered signed-log transport field**:

```text
χ_tan,ctr(λ) = sign(χ_raw(λ)) · log(1 + |χ_raw(λ)|) - median_λ[ sign(χ_raw(λ)) · log(1 + |χ_raw(λ)|) ]
```

where χ_raw is built from the local transport-order commutator and the local mixed-curvature area.

## Suite summary at the switch γ

- benchmark_a: Phase 14 verdict=None, Phase 15 verdict=null_like, switch γ=0.30, structural amplitude=0.027735545484517843, valid cells=36, zero-crossing u=None, comparison corr=None, comparison R²=None
- benchmark_b: Phase 14 verdict=None, Phase 15 verdict=weak_control, switch γ=0.30, structural amplitude=2.057075806571863, valid cells=33, zero-crossing u=None, comparison corr=None, comparison R²=None
- benchmark_c: Phase 14 verdict=structured_sign_boundary, Phase 15 verdict=generator_structured_sign_boundary, switch γ=0.30, structural amplitude=9.063568785210055, valid cells=34, zero-crossing u=-0.039865143568660784, comparison corr=0.9805868137936634, comparison R²=0.9615504993860086
- benchmark_d: Phase 14 verdict=None, Phase 15 verdict=null_like, switch γ=0.30, structural amplitude=2.370753947527076, valid cells=32, zero-crossing u=None, comparison corr=None, comparison R²=None
- benchmark_f: Phase 14 verdict=None, Phase 15 verdict=excluded_R4, switch γ=0.30, structural amplitude=0.0, valid cells=0, zero-crossing u=None, comparison corr=None, comparison R²=None

## Focus benchmark interpretation

Focus benchmark: **benchmark_c**.
At switch γ=0.30, the centered tangent field has structural amplitude 9.063568785210055 and 6 zero-crossing samples.
Against the Phase 14 empirical field on overlapping valid cells: corr=0.9805868137936634, R²=0.9615504993860086, sign agreement=1.0, overlap count=25.

| variant | structural amplitude | valid cells | mean zero-crossing u |
|---|---:|---:|---:|
| primary mesh=7 | 9.063568785210055 | 34 | -0.039865143568660784 |
| dense mesh=11 | 16.060113860177147 | 88 | -0.08013769617603243 |
| secondary observable=final_p1 | 1.7834959169929192 | 34 | None |

## Interpretation

- The tangent-derived field adds a more direct generator-side explanation of the noisy local structure.
- Benchmark C remains the key positive noisy benchmark: its centered tangent field predicts a sign boundary near the control-space center and aligns strongly with the Phase 14 field.
- Benchmarks A and D retain their null-like accepted role; their tangent fields are dominated by a smooth benchmark-level baseline rather than a strong structural boundary.
- Benchmark B remains weak-control rather than a robust positive case.
- Benchmark F remains excluded by R4 and is not interpreted through the tangent field.

Suite plot: `/mnt/data/CWT-CGT_Project/05_reports/plots/phase15_tangent_field/suite_structural_amplitude.png`
