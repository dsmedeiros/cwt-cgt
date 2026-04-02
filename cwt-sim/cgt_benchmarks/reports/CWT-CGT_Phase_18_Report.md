# CWT-CGT Phase 18 Report

## What Phase 18 adds

Phase 18 replaces neighbor-estimated Hamiltonian and jump-operator tangents with benchmark-specific analytic branch tangents.

The benchmark-specific control derivatives are propagated through:
- branch probability logits,
- branch phase differences,
- kernel entries,
- branch Hamiltonian entries,
- jump-operator amplitudes,
- and finally the Lindblad generator Jacobian.

## Suite summary at the switch slice

- benchmark_a: verdict=`null_like`, structural amplitude=`0.0000`, valid cells=`36`
- benchmark_b: verdict=`weak_control`, structural amplitude=`1.1810`, valid cells=`33`
- benchmark_c: verdict=`analytic_tangent_sign_boundary`, structural amplitude=`12.2207`, valid cells=`34`, mean zero crossing u=`-0.0467`
- benchmark_d: verdict=`null_like`, structural amplitude=`2.1818`, valid cells=`32`
- benchmark_f: verdict=`excluded_R4`, structural amplitude=`0.0000`, valid cells=`0`

## Focus benchmark interpretation

Focus benchmark: `benchmark_c`.
At the switch point \(\gamma = 0.30\):

- structural amplitude = **12.2207**
- valid cells = **34**
- mean zero crossing = **-0.0467**
- corr vs Phase 14 empirical field = **0.9736**
- corr vs Phase 17 Fréchet field = **0.999992**
- affine-fit \(R^2\) vs Phase 17 = **0.999985**
- sign agreement vs Phase 17 = **1.0**

Dense-mesh stability for benchmark C:
- primary mesh = `7` with zero crossing `-0.0467`
- dense mesh = `11` with zero crossing `-0.0958`

## Interpretation

Phase 18 does not change the noisy benchmark story qualitatively. It mostly cleans up the derivation.

The positive noisy benchmark still shows the same left-of-center sign-boundary picture, but now through a benchmark-specific analytic tangent model rather than mesh-estimated tangents.
