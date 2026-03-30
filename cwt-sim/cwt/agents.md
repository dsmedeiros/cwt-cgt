---
scope: "cwt-sim/cwt"
governs: "Core simulation engine — geometry, layers, orchestrator, metrics, noise, operator modules"
inherits: "AGENTS.md"
adrs: [ADR-0001, ADR-0003]
invariants: [LAYER-001, LAYER-002, LAYER-003, GEOM-001, GEOM-002, GEOM-003]
enforced-by:
  - cwt-sim/tests/unit/test_layer_updates.py
  - cwt-sim/tests/unit/test_curvature_estimator.py
  - cwt-sim/tests/unit/test_metric_estimator.py
  - cwt-sim/tests/unit/test_geometric_couplings.py
  - .github/workflows/tests.yml
persona: implementer
authority: [read, write, test]
restricted: [cross-cutting-changes, schema-migration]
---

# CWT Core Simulation Engine

## Overview

The core engine implementing CWT/CGT dynamics on graph substrates. Contains geometry estimators (metric, curvature, Fubini-Study, gauge, adaptive mesh), three-layer dynamics (Q, Theta, state), orchestration (scheduler, param_path), metrics/evaluation, noise models, and operator modules. This is the mathematical heart of the project.

## Behavioral Directives

- **Must:** Keep layer update functions pure — no hidden state, no side effects, no input mutation (LAYER-001).
- **Must:** Pass geometric corrections as explicit parameters to layer updates (LAYER-003).
- **Must not:** Import between layer modules (q_update, theta_update, state) — coupling goes through orchestrator only (LAYER-002).
- **Must not:** Import from layers/, orchestrator/, experiments/, or baselines/ within geometry modules (GEOM-001).
- **Always:** Accept explicit graph and field arrays in geometry functions — no global state (GEOM-002).
- **Always:** Handle degenerate graphs (single node, disconnected) gracefully (GEOM-003).
- **Never:** Add dependencies on cwt_lab/ or external visualization libraries.

## Change Expectations

- Preserve the three-layer separation (Q, Theta, State).
- Preserve the geometry module independence.
- Preserve the orchestrator as the sole composition point for cross-layer data flow.
- Preserve existing test contracts — new features must have unit tests.

## Cross-Links

- **Parent directives:** `AGENTS.md`
- **Governing ADRs:** ADR-0001 (three-layer model), ADR-0003 (geometric estimator separation)
- **Related components:** `cwt-sim/baselines/agents.md` (validates against core outputs), `cwt-sim/experiments/agents.md` (consumes core API)
- **Invariants:** See `.armature/invariants/registry.yaml` for entries: LAYER-001, LAYER-002, LAYER-003, GEOM-001, GEOM-002, GEOM-003
