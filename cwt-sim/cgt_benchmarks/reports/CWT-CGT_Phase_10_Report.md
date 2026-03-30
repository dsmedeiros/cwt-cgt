# CWT-CGT Phase 10 Report

## What Phase 10 adds

Phase 10 replaces the earlier operational noisy surrogate with a **graph-local open-system CPTP lane** and adds a genuine **mixed-state holonomy / curvature object**.

The open-system step is built from:
- a branch-local coherent Hamiltonian derived from symmetric edge couplings and branch phases,
- local directed jump operators derived from the graph kernel,
- sitewise dephasing operators,
- and a small depolarizing background for numerical stability.

The mixed-state geometric object is an **Uhlmann-like holonomy** formed from polar link unitaries between neighboring density amplitudes. Bures metric traces remain the metric side of the mixed-state lane.

## Current benchmark-C result

Recommended mixed-state switch: **γ ≈ 0.20**.

Global fit at the switch point:
- slope = 3407.343773480347
- R² = 0.5572338051193161
- trusted pair count = 6

Patchwise fits at the switch point:
- center (0.00,0.00): slope=3414.492416716142, R²=0.8151365024928436, count=4
- center (-0.20,0.20): slope=None, R²=None, count=1
- center (0.20,0.20): slope=None, R²=None, count=1

Coherence trend:
- γ grid = [0.0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4]
- mean |mixed curvature| by γ = ['8.397e-07', '7.749e-07', '7.363e-07', '7.060e-07', '6.792e-07', '6.300e-07', '5.833e-07']

## Interpretation

Phase 10 supports the stronger claim that the noisy lane is now tied to a **graph-local open-system rule** rather than direct target interpolation. It also upgrades the mixed-state phase object from a placeholder to a real holonomy diagnostic.

The fit remains patchwise. That means the theory should continue to state the noisy law as a local susceptibility law rather than as a single universal global coefficient.
