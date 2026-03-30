# Invariants

Hard rules extracted from ADRs. Violations block commits via reviewer gate.

---

## Layer Dynamics

| ID | Severity | Rule | Rationale | Enforcement |
|---|---|---|---|---|
| LAYER-001 | critical | Layer update functions must be pure — no hidden state, side effects, or input mutation | Enables independent testing and deterministic replay | `test_layer_updates.py` |
| LAYER-002 | critical | Layer modules must not import from each other | Cross-layer coupling flows through orchestrator only | Post-stop import check (TODO) |
| LAYER-003 | high | Geometric corrections passed as explicit parameters, never computed inside layers | Keeps geometry swappable without touching dynamics | `test_layer_updates.py` (TODO) |

## IPC Bridge

| ID | Severity | Rule | Rationale | Enforcement |
|---|---|---|---|---|
| IPC-001 | critical | Renderer must never import from electron/ or spawn processes | All Python interaction through IPC bridge | Import boundary lint (TODO) |
| IPC-002 | high | IPC handlers validate inputs with shared Zod schemas | Runtime type safety across process boundary | `ipc.artifacts.test.ts` |
| IPC-003 | high | Python env detection uses progressive fallback chain | No hardcoded paths — works on any dev machine | `env.sanitize.test.ts` |
| IPC-004 | high | Every Python invocation has configurable timeout | No unbounded waits that freeze the UI | `runManager.integration.test.ts` |

## Geometric Estimators

| ID | Severity | Rule | Rationale | Enforcement |
|---|---|---|---|---|
| GEOM-001 | critical | Geometry modules must not import from layers/, orchestrator/, experiments/, baselines/ | Maintains estimator independence and testability | Post-stop import check (TODO) |
| GEOM-002 | high | Geometry functions accept explicit graph/field arrays — no global state | Enables synthetic-input testing | `test_curvature_estimator.py`, `test_metric_estimator.py` |
| GEOM-003 | high | Estimators handle degenerate graphs without unhandled exceptions | Single-node and disconnected graphs are valid inputs | `test_curvature_estimator.py` |

## Baselines

| ID | Severity | Rule | Rationale | Enforcement |
|---|---|---|---|---|
| BASE-001 | high | Every baseline runner exposes `run()` with consistent return schema | Enables automated comparison pipeline | `test_sis_run.py`, `test_ising_run.py` |
| BASE-002 | high | Fixture CSVs are append-only — no modification without ADR amendment | Regression anchors must be stable | Pre-commit hook (TODO) |
| BASE-003 | critical | Baseline runners must not import from cwt/ | Independent reference implementations | Post-stop import check (TODO) |

## Gate Progression

| ID | Severity | Rule | Rationale | Enforcement |
|---|---|---|---|---|
| GATE-001 | high | Experiments above stage0 require passing stage0 analytic checks | Validates foundation before building on it | `test_stage0_analytic.py` |
| GATE-002 | high | Artifacts written to experiment's own artifacts/ directory only | Prevents cross-experiment contamination | Path check (TODO) |
| GATE-003 | medium | Each experiment's run.py invokable as standalone Typer CLI | Enables CI and scripted execution | `test_loop_at_hotspot_cli.py` |

## Desktop Lab

| ID | Severity | Rule | Rationale | Enforcement |
|---|---|---|---|---|
| LAB-001 | high | Renderer must not contain simulation validation logic — use shared/ Zod | Single source of truth for type contracts | `validators.test.ts` |
| LAB-002 | medium | Cross-component state uses Zustand stores, not component-local state | Predictable state flow | Lint rule (TODO) |
| LAB-003 | medium | Desktop lab functions in demo mode without Python | Enables UI development without full stack | `DemoModeContext.tsx` |
