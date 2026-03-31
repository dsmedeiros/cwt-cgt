# CWT-CGT Theory — Hardened v13

## Current core claim

The core theory remains a **branch-resolved geometric-response framework** for local graph dynamics. In trusted coherent regions, the geometry of branch-resolved states over exogenous controls predicts sensitivity and orientation-dependent loop response. Branch switching, topology, and noisy mixed-state behavior live in separate lanes and are reported only under their own validity conditions.

## What v13 changes

v13 refines the noisy lane again. The mixed-state response is no longer described only as a discrete patch-family atlas. It is now described as a **smoothed local mixed-state field** built from generator-driven minimal plaquettes:

```text
ΔR_γ ≈ χ_mix(λ, b; γ) · Φ_mix(λ, b; γ)
```

but only **locally**, only on trusted cells, and only after a mixed-holonomy floor and effective-support filter.

The Phase 13 patch atlas remains useful as a coarse report, but v13 treats it as a summary layer rather than the fundamental noisy object.

## Why the theory changed

Phase 13 showed that the noisy lane was real but locally fragmented. The next scientific question was whether that fragmentation was only an artifact of a few chosen loop families.

Phase 14 answers that question more directly: when the noisy lane is reconstructed from **minimal plaquettes of the Lindblad-style generator**, benchmark C still shows structured local response, while A and D remain null-like, B remains weak, and F remains excluded by R4.

So the theory now points toward a **local mixed-state field picture**, not just a small table of patch fits.

## Current benchmark status at the noisy switch point

- **benchmark_a**: null_like at switch γ=0.30. Valid local-field cells = 0.
- **benchmark_b**: weak_control at switch γ=0.30. Valid local-field cells = 0.
- **benchmark_c**: structured_sign_boundary at switch γ=0.30. Valid local-field cells = 25, mean zero-crossing location in control-1 = -0.0275461, mean sign consistency = 0.723118.
- **benchmark_d**: null_like at switch γ=0.30. Valid local-field cells = 0.
- **benchmark_f**: excluded_R4 at switch γ=0.30. Valid local-field cells = 0.

## Interpretation of the positive noisy benchmark

Benchmark C remains the key positive noisy benchmark, but v13 sharpens the statement again.

The correct noisy claim is **not** that there is one benchmark-wide coefficient, and it is not merely that a few manually chosen patch families fit well. The correct statement is that benchmark C supports a **structured local mixed-state field** with a stable sign boundary near the center of control space.

At the switch point γ=0.30:

- the smoothed field has 25 valid cells;
- the mean sign-boundary location is control-1 ≈ -0.0275461;
- the sampled field at **(0.00, 0.00)** is χ ≈ 12.679 with consistency ≈ 0.507066;
- the sampled field at **(0.18, 0.00)** is χ ≈ 126.767 with consistency ≈ 0.895362.

That means the positive noisy benchmark is now best read as a **field with a nearby sign boundary**, not just as a list of positive and negative patches.

## What the theory now claims confidently

1. The coherent/passive branch-resolved core is much stronger than the original draft.
2. Branch switching must be modeled separately from smooth pumping.
3. Topological claims belong only to the auxiliary periodic/gapped sector.
4. The noisy lane is real enough to keep, but it should be reported as a **local mixed-state field** rather than a global coefficient.
5. Minimal generator-driven plaquettes preserve the positive noisy benchmark while the null controls stay null-like at the switch point.

## What the theory does not yet claim

- It does not yet claim a final microscopic derivation of the Lindblad-style generator directly from the nonlinear graph update rule.
- It does not yet claim a full mixed-state topological sector.
- It does not yet claim that the smoothed mixed-state field is the final or unique coarse-grained object.
- It does not yet claim that the noisy lane becomes globally simple once it is smoothed.

## Bottom line

v13 makes the noisy lane more local, more generator-tied, and more honest. The project is still strongest as a **layered research framework** with a validated coherent core, a separated R4 branch-switching lane, an auxiliary topology lane, and a noisy lane that now looks best as a **structured local field over control space**.
