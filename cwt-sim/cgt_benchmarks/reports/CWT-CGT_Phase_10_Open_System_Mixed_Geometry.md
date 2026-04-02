# CWT-CGT Phase 10 — Graph-Local Open-System Lane and Mixed-State Geometry

## Goal

Phase 10 strengthens the noisy extension by replacing the old target-interpolation surrogate with a graph-local CPTP update and by giving the mixed-state lane a genuine holonomy / curvature diagnostic.

## Construction

For each branch state (p, θ, K), define:

- a branch Hamiltonian H from symmetric edge couplings and phase differences,
- directed jump operators from the graph kernel K,
- sitewise dephasing operators controlled by γ,
- a small depolarizing background for stability.

The effective mixed branch density is the K-step image of the pure branch state under that local channel.

## Geometry used in Phase 10

- metric: Bures finite-difference trace;
- phase: Uhlmann-like holonomy from polar link unitaries;
- curvature: plaquette holonomy phase divided by area.

## Current benchmark-C result

- switch γ ≈ 0.20
- global fit at switch: slope ≈ 3407.343773480347, R² ≈ 0.5572338051193161, count = 6
- central patch fit at switch: slope ≈ 3414.492416716142, R² ≈ 0.8151365024928436, count = 4

## Interpretation boundary

Phase 10 supports a stronger noisy extension, but it still does **not** justify mixed-state topological claims. The current mixed-state holonomy is a benchmarked diagnostic, not yet a topology-grade invariant.
