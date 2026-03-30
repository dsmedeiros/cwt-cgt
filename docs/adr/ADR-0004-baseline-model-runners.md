# ADR-0004: Baseline Model Runners

**Status:** Accepted
**Date:** 2026-03-30
**Supersedes:** N/A

## Context

CWT simulations need validation against known physics — Ising, Kuramoto oscillators, bond percolation, and SIS epidemics. Each baseline model has canonical behavior on standard graph topologies. A consistent runner interface allows automated comparison between CWT predictions and baseline ground truth.

## Decision

Baseline model runners live in `cwt-sim/baselines/` with one sub-package per model:
- `ising/run.py`, `kuramoto/run.py`, `percolation/run.py`, `sis/run.py`.
- Each runner exposes a `run()` function accepting a graph and model-specific parameters.
- A shared `common.py` provides fixture loading, result formatting, and comparison utilities.
- Fixture data lives in `baselines/__fixtures__/` as CSV files.
- Tests in `baselines/__tests__/` validate runner outputs against fixture baselines.

## Consequences

- Adding a new baseline model requires only a new sub-package with a `run()` entry point.
- Baseline comparison is automated — fixture CSVs serve as regression anchors.
- CWT experiment workflows can invoke baselines programmatically for head-to-head comparison.

## Invariants

- **BASE-001:** Every baseline runner must expose a `run()` function with a consistent return schema (dict with keys: `steps`, `observables`, `metadata`).
- **BASE-002:** Fixture CSV files are append-only. Existing fixture data must not be modified without explicit ADR amendment.
- **BASE-003:** Baseline runners must not import from cwt/ modules. They implement independent reference models.

## Non-Goals

- This ADR does not specify the statistical comparison method between CWT and baselines.
- This ADR does not cover GPU acceleration of baseline models.

## Observability

Baseline runner invocations and wall-clock times are printed to stdout. Fixture comparison results include per-observable deltas.

## Security Considerations

No additional security considerations beyond existing baseline.

## Acceptance Criteria

- [ ] Each baseline runner has a `run()` function matching the declared return schema.
- [ ] Each baseline has at least one fixture CSV and a test validating against it.
- [ ] No baseline module imports from cwt/.
