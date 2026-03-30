# ADR-0005: Gate-Based Experiment Progression

**Status:** Accepted
**Date:** 2026-03-30
**Supersedes:** N/A

## Context

The research workflow moves through stages of increasing complexity — from analytic sanity checks (stage0) through parameter sweeps (gateA), ridge finding (gateB), topology robustness (gateC), and optional CHSH tests (gateD). Each gate has entry criteria that must be satisfied before the next stage is meaningful. Without explicit gating, experiments can produce misleading results by running on unvalidated foundations.

## Decision

Experiments in `cwt-sim/experiments/` are organized by gate:
- `stage0_analytic/` — Closed-form verification on small graphs.
- `gateA_rho_tau_loop/` — Parameter sweep for coupling strength.
- `gateB_ridge_finder/` — Statistical ridge detection in parameter space.
- `gateC_topology_robust/` — Cross-topology invariance checks.
- `gateD_chsh_optional/` — Optional Bell-inequality-like tests.
- Additional experiments (`wilson_loop_3d`, `torus_plateau`, `inverse_design`, etc.) target specific research questions but reference gate prerequisites.

Each experiment directory contains a `run.py` with a CLI entry point and optionally an `artifacts/` directory for outputs and a `REPORT.md` for findings.

## Consequences

- Gate ordering provides a natural validation pipeline.
- Experiments can declare gate prerequisites to prevent premature execution.
- Report artifacts are co-located with experiment code.
- New experiments slot into the gate hierarchy or reference existing gates.

## Invariants

- **GATE-001:** No experiment above stage0 may be considered validated unless stage0 analytic checks pass on the same graph family.
- **GATE-002:** Experiment artifacts must be written to the experiment's own `artifacts/` directory, never to shared locations.
- **GATE-003:** Each experiment's `run.py` must be invokable as a standalone CLI command via Typer.

## Non-Goals

- This ADR does not enforce automated gate checking in CI (future work).
- This ADR does not specify report format beyond the REPORT.md convention.

## Observability

Experiment runs log start/end times, parameter configurations, and output artifact paths to stdout.

## Security Considerations

No additional security considerations beyond existing baseline.

## Acceptance Criteria

- [ ] Each experiment directory contains a `run.py` with a Typer CLI entry point.
- [ ] Experiment artifacts do not write outside their own `artifacts/` directory.
- [ ] Stage0 tests pass on standard graph families (ring, grid, torus).
