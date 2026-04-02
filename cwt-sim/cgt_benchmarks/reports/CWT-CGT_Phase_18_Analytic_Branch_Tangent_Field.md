# CWT-CGT Phase 18 — Analytic Branch-Tangent Field

## Goal

Phase 18 replaces mesh-estimated noisy control tangents with benchmark-specific analytic control tangents of the branch maps.

The new construction takes analytic or piecewise-analytic derivatives of the benchmark branch ingredients
\(p(\lambda)\), \(	heta(\lambda)\), and \(K(\lambda)\), lifts them into analytic tangents of the branch Hamiltonian and jump operators, and then assembles a generator Jacobian field.

## Accepted Phase 18 object

At each trusted cell, the accepted noisy structural object is still a centered signed-log field, but the derivative source is now analytic:

```text
D_u L = D L[(d_u H, {d_u L_k})]
D_v L = D L[(d_v H, {d_v L_k})]
Xi_A = [D_u L, D_v L] rho_bar
chi_A,ctr = sign(chi_raw) log(1 + |chi_raw|) - median_lambda(sign(chi_raw) log(1 + |chi_raw|))
```

The project now treats this Phase 18 field as the cleanest benchmark-specific noisy structural predictor so far.

## Why it matters

Phase 17 improved the noisy lane by assembling the superoperator Jacobian analytically once the control tangents of the Hamiltonian and jump operators were known. But those tangents were still estimated from neighboring mesh states.

Phase 18 removes that dependency. The noisy structural field is now driven by explicit branch-model tangents. That tightens the derivation without broadening the claim.
