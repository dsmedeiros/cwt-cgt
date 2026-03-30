# ADR-0003: Geometric Estimator Separation

**Status:** Accepted
**Date:** 2026-03-30
**Supersedes:** N/A

## Context

The CWT/CGT framework computes metric tensors, curvature, Fubini-Study distances, and gauge fields on graph substrates. These geometric quantities feed into layer dynamics and experiment readouts. Mixing geometric computation with dynamics or I/O code would make the system untestable and opaque.

## Decision

All geometric estimators live in `cwt-sim/cwt/geometry/` as standalone modules:
- `metric.py` — Metric tensor estimation on graph edges.
- `curvature.py` — Discrete curvature from metric data.
- `psi.py` — Wavefunction utilities and complex state construction.
- `fs_distance.py` — Fubini-Study distance between states.
- `gauge.py` — Gauge field computation.
- `thermometer.py` — Temperature-like observables from geometric data.
- `adapt_mesh.py` — Adaptive mesh refinement based on curvature.

Each module exposes pure functions that accept graph structure and field arrays, returning geometric quantities. No module in `geometry/` imports from `layers/`, `orchestrator/`, or `experiments/`.

## Consequences

- Geometric estimators are testable with synthetic graph/field data.
- New estimators can be added without touching dynamics code.
- Experiment readouts compose geometric quantities from the module API.
- The orchestrator passes geometric outputs to layer updates as parameters.

## Invariants

- **GEOM-001:** Geometry modules must not import from layers/, orchestrator/, experiments/, or baselines/.
- **GEOM-002:** All geometry functions must accept explicit graph and field arrays — no global state access.
- **GEOM-003:** Curvature and metric estimators must handle degenerate graphs (single node, disconnected components) without raising unhandled exceptions.

## Non-Goals

- This ADR does not mandate specific numerical algorithms for estimators.
- This ADR does not cover visualization of geometric quantities.

## Observability

Geometry module calls are timed when the orchestrator runs in verbose mode. Degenerate-graph fallback paths log warnings.

## Security Considerations

No additional security considerations beyond existing baseline.

## Acceptance Criteria

- [ ] No geometry module imports from layers/, orchestrator/, experiments/, or baselines/.
- [ ] Each geometry module has unit tests covering at least one non-trivial and one degenerate graph case.
- [ ] Orchestrator passes geometry outputs as explicit parameters to layer updates.
