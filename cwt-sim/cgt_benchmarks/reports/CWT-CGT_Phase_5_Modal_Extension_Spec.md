# CWT-CGT Phase 5 — Modal Extension Spec

## 1. Purpose

Phase 5 upgrades the passive geometric theory from a state-only description to a **mode-resolved branch geometry**.
Its job is to explain the local signed-flux response coefficient

\[
\Delta R_\gamma \approx \chi(\lambda_0,b)\,\Phi_\gamma
\]

in terms of a small set of dominant modes of a branch-local operator.

The modal extension is **not** allowed to alter the validated passive benchmark block.
It must sit on top of it and explain it.

## 2. Entry conditions

Phase 5 begins only after the following are already true.

1. The passive scan atlas runs with explicit branch continuation and R4 exclusion.
2. The null benchmarks remain null under baseline and robustness protocols.
3. The positive ring benchmark survives baseline square, held-out circle, and off-center patchwise checks.
4. The package imports cleanly and the benchmark scaffold is reproducible.

## 3. Objects to define

### 3.1 Branch-local operator

For each trusted branch point \((\lambda,b)\), define a linear response operator.
There are two acceptable entry points.

- **Jacobian route**: use the branch Jacobian of the full local update map,
  \[
  M(\lambda,b)=\partial_x T_\lambda\big|_{x_*},
  \]
  where \(x=(p,\theta)\).
- **Auxiliary operator route**: use an implementation-ready surrogate operator \(L(\lambda,b)\) that approximates the same branch-local response and is clearly marked as an auxiliary model.

The first released modal layer may use the auxiliary route if the full Jacobian is not yet exposed everywhere in code.

### 3.2 Left/right modes

For the chosen operator, compute right and left modes,

\[
L u_a^R = \mu_a u_a^R,
\qquad
\langle u_a^L|L = \mu_a \langle u_a^L|.
\]

Biorthogonal normalization is required,

\[
\langle u_a^L|u_b^R\rangle = \delta_{ab},
\]

up to documented numerical tolerance.

### 3.3 Modal connection

Define the mode-resolved connection between neighboring trusted points,

\[
A_i^{ab}(\lambda,b)=\langle u_a^L|\partial_i u_b^R\rangle,
\]

or its discrete overlap analog on the benchmark mesh.

The diagonal entries describe modewise geometric phase accumulation.
The off-diagonal entries diagnose non-adiabatic mixing.

## 4. Primary outputs of Phase 5

Phase 5 should produce five benchmark-facing outputs.

### 4.1 Gap map

For each trusted scan tile, estimate a dominant spectral gap relative to the mode or subspace that controls branch following.
This is the first mechanistic explanation for where the passive geometry becomes soft or fragile.

### 4.2 Modal Wilson phase

Along a trusted loop, compute a discrete modal Wilson phase for the dominant mode or dominant subspace.
This should be compared to the existing state-based signed flux estimator.

### 4.3 Mixing diagnostic

Compute a non-adiabatic or cross-mode mixing score from the off-diagonal modal connections.
This helps separate clean R1 behavior from near-R2 contamination.

### 4.4 Patchwise susceptibility explanation

Use the modal data to explain why two trusted centers can have the same sign law but different slope magnitudes.
This is the central target of the Phase 5 upgrade.

### 4.5 Exceptional or near-degenerate warnings

When the gap is small or the biorthogonality error grows, Phase 5 must emit a warning rather than silently overclaim a clean modal interpretation.

## 5. Minimum code interface

The current scaffold now includes a `modal.py` helper module.
The minimum Phase 5 interface should expose:

- `biorthogonal_modal_frame(operator)`
- `mode_connection(frame_a, frame_b)`
- `mode_wilson_phase(frames, mode_index)`

These are not yet the full theory; they are the implementation anchor for the next layer.

## 6. Validation sequence

### Stage 5A — Static modal checks

For each benchmark scan tile in trusted regions:

- compute modal frames,
- record spectral gaps,
- record biorthogonality error,
- verify numerical stability.

### Stage 5B — Loop comparison

For trusted loop families:

- compute state-based signed flux,
- compute modal Wilson phase,
- compare sign and monotonicity.

This stage is successful if the modal quantity tracks the observed signed response at least as well as the raw state flux on the positive benchmark without creating false positives on null benchmarks.

### Stage 5C — Patchwise slope explanation

For the off-center positive protocols:

- compare per-center passive slopes,
- compare per-center modal gap/connection summaries,
- test whether the variation in slope magnitude is predictable from the modal data.

This is the step that turns the off-center robustness result into a real explanatory gain.

## 7. What Phase 5 does not yet claim

Phase 5 is still not the topological lane.
It does not by itself justify integer Chern claims.
It also does not reintroduce direct geometric forcing into the core dynamics.

The modal layer remains an **explanatory extension**, not a replacement for the hardened passive core.

## 8. Exit criteria

Phase 5 is considered successful when all of the following hold.

1. Modal frames can be computed reproducibly on trusted scan tiles.
2. The dominant gap map correlates with passive softness and sensitivity hotspots.
3. Modal Wilson phases track the sign-reversing pump on the positive benchmark.
4. Null benchmarks remain null under the same modal analysis.
5. Off-center patchwise slope changes have a coherent modal explanation.

At that point the theory will have moved from “geometry predicts response” to “branch-local modes explain why different trusted patches respond the way they do.”
