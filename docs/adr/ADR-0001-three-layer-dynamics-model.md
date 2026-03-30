# ADR-0001: Three-Layer Dynamics Model

**Status:** Accepted
**Date:** 2026-03-30
**Supersedes:** N/A

## Context

CWT simulations require a structured representation of field dynamics on graph substrates. The mathematical framework defines three coupled fields — probabilistic mass (Q), relative phase (Theta), and curvature corrections (C) — that evolve under geometric constraints. A clear separation of these layers is needed to allow independent testing, modular updates, and clean composition.

## Decision

All simulation dynamics are organized into three distinct layers implemented in `cwt-sim/cwt/layers/`:
- **Q layer** (`q_update.py`): Probabilistic mass flow on graph edges.
- **Theta layer** (`theta_update.py`): Relative phase evolution with frustration and zeta-phase corrections.
- **State layer** (`state.py`): Combined state vector management and initialization.

Each layer exposes a pure-function update interface that takes the current state and parameters, returning the next state. Geometric corrections from `cwt/geometry/` are injected as parameters, not embedded in layer logic.

## Consequences

- Layer modules can be tested independently with synthetic inputs.
- Geometric estimators can be swapped or refined without touching layer code.
- Composition order is explicit in the orchestrator scheduler.
- Adding a fourth layer (e.g., for noise coupling) requires orchestrator changes but not layer refactoring.

## Invariants

- **LAYER-001:** Each layer update function must be pure — no hidden state, no side effects, no mutation of input arrays.
- **LAYER-002:** Layer modules must not import from each other. Cross-layer coupling flows through the orchestrator only.
- **LAYER-003:** Geometric corrections must be passed as explicit parameters, never computed inside layer modules.

## Non-Goals

- This ADR does not prescribe the internal algorithm of any layer update.
- This ADR does not cover readout/observable extraction (see ADR-0003).

## Observability

Layer update timing and per-step norms are logged by the orchestrator scheduler when verbose mode is enabled.

## Security Considerations

No additional security considerations beyond existing baseline.

## Acceptance Criteria

- [ ] Each layer module has independent unit tests with synthetic graph inputs.
- [ ] No cross-imports exist between q_update.py, theta_update.py, and state.py.
- [ ] Orchestrator scheduler calls layers in documented order with explicit parameter passing.
