# CWT-CGT Theory — Hardened v14

## Current core claim

The core theory remains a **branch-resolved geometric-response framework** for local graph dynamics. In trusted coherent regions, the geometry of branch-resolved states over exogenous controls predicts sensitivity and loop-orientation-dependent response. Branch switching, topology, and noisy mixed-state behavior remain separate lanes and are reported only under their own validity conditions.

## What v14 changes

v14 adds a new noisy-lane object: a **generator-derived structural tangent field** built from local transport-order commutators of the Lindblad-style generator. The accepted Phase 15 tangent quantity is the **centered signed-log transport field**:

```text
χ_tan,ctr(λ) = sign(χ_raw(λ)) · log(1 + |χ_raw(λ)|) - median_λ[sign(χ_raw(λ)) · log(1 + |χ_raw(λ)|)]
```

where `χ_raw` is formed from the local ordered-transport gap divided by the local mixed-curvature area.

This object does **not** replace the empirical Phase 14 local field. It is a **generator-side structural predictor** for that field.

## Why the theory changed

Phase 14 showed that the noisy lane in benchmark C is best described as a smoothed local field with a sign boundary. The next question was whether that field could be recovered more directly from the generator rather than only from minimal-plaquette response reconstruction.

Phase 15 answers that positively for benchmark C. At the switch point `γ = 0.30`, the centered tangent field:

- has structural amplitude `9.063568785210055`,
- has mean zero-crossing location `u ≈ -0.039865143568660784`,
- overlaps the Phase 14 field on `25` valid cells,
- matches it with correlation `0.9805868137936634` and affine-fit `R² = 0.9615504993860086`,
- and has sign agreement `1.0`.

So the noisy extension is now best understood as **two linked objects**:

1. an empirical local mixed-state field (Phase 14), and
2. a generator-derived structural tangent predictor (Phase 15).

## Current benchmark picture at the switch point

- **benchmark_a**: `null_like`. Structural amplitude `0.027735545484517843`.
- **benchmark_b**: `weak_control`. Structural amplitude `2.057075806571863`.
- **benchmark_c**: `generator_structured_sign_boundary`. Structural amplitude `9.063568785210055`, mean zero crossing `-0.039865143568660784`.
- **benchmark_d**: `null_like`. Structural amplitude `2.370753947527076`.
- **benchmark_f**: `excluded_R4`.

## Stability of the positive noisy benchmark

For benchmark C, the tangent sign boundary is stable under dephasing in the current grid:

- at `γ = 0.00`: zero crossing `u ≈ -0.03977208113756716`,
- at `γ = 0.10`: zero crossing `u ≈ -0.039919898207426384`,
- at `γ = 0.20`: zero crossing `u ≈ -0.039894975279968624`,
- at `γ = 0.30`: zero crossing `u ≈ -0.039865143568660784`.

It also persists under a denser mesh check:

- primary mesh `7`: zero crossing `u ≈ -0.039865143568660784`,
- dense mesh `11`: zero crossing `u ≈ -0.08013769617603243`.

The secondary observable lane is weaker: for `final_p1`, the structural amplitude is only `1.7834959169929192` and no robust zero-crossing is accepted in this pass.

## What the theory now claims confidently

1. The coherent/passive branch-resolved core remains the strongest part of the project.
2. Branch switching must remain separate from smooth geometric pumping.
3. Topology stays quarantined to the auxiliary periodic/gapped sector.
4. The noisy lane is not a single global coefficient. It is an empirical local field plus a generator-derived structural tangent predictor.
5. Benchmark C now has both an empirical local field (Phase 14) and a generator-side tangent field that agree strongly on structure and sign.

## What the theory still does not claim

- It does not yet claim a final microscopic derivation of the open-system generator directly from the nonlinear graph rule.
- It does not yet claim that the tangent field alone is a full quantitative replacement for the empirical field.
- It does not yet claim a full mixed-state topological sector.
- It does not yet claim that every observable should inherit the same positive noisy sign boundary.

## Status of the old patch atlas

The Phase 13 patch-family atlas is now best treated as a **deprecated intermediate reporting layer**. It remains useful for historical comparison, but the accepted noisy objects are now:

- the Phase 14 smoothed local mixed-state field, and
- the Phase 15 centered generator-tangent field.

## Bottom line

v14 makes the noisy lane more mechanistic without pretending it is final. The project is still best understood as a **layered benchmarked framework**: a strong coherent core, a separate R4 branch-switching lane, a quarantined auxiliary topology lane, an empirical noisy local field, and now a generator-derived tangent predictor that explains the positive noisy benchmark’s sign structure.
