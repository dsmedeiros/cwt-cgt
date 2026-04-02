# CWT-CGT Phase 6 — Explicit Jacobian Route

## Goal

Replace the auxiliary-operator-only explanation with a more directly derived branch-local response mechanism.

## Implemented objects

For each trusted branch point \((\lambda,b)\), the project now computes:

- a branch-local relaxation map \(T^{(b)}_\lambda\),
- a numerical Jacobian \(M=\partial_xT\vert_{x_*}\),
- control-coupling vectors \(B_i\),
- response vectors \(r_i=(I-M)^{-1}B_i\),
- a Jacobian-derived local metric and curvature,
- a Jacobian-derived predicted signed loop flux.

## Accepted Jacobian observable

The accepted loop observable in this phase is

\[
\widehat\Phi_\gamma = \overline{\widehat\Omega}_\gamma A_\gamma,
\]

with \(\overline{\widehat\Omega}_\gamma\) implemented as the path-mean Jacobian-derived curvature.

## Why this is stronger than the auxiliary modal surrogate

The auxiliary modal route can show that a mode tracks the state geometry.
The explicit Jacobian route shows where the local sensitivity and local loop bias come from in terms of a branch-local linear response operator.

That is a more foundational gain.

## Current outcome

- strong scan-side explanation on benchmark B,
- strong scan-side and loop-side explanation on benchmark C,
- null behavior preserved on A and D,
- weak Jacobian modal-phase law, which remains secondary.

## Main open issue

The current explicit Jacobian route still has a sign-convention mismatch in curvature and a weak single-mode holonomy signal.
So the next upgrade should refine the complex tangent operator and gauge handling rather than declaring victory on the modal holonomy sub-layer.
