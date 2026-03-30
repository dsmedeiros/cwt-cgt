---
scope: "cwt-sim/experiments"
governs: "Research workflows with gate-based progression (stage0 through gateD)"
inherits: "AGENTS.md"
adrs: [ADR-0001, ADR-0003, ADR-0005]
invariants: [GATE-001, GATE-002, GATE-003]
enforced-by:
  - cwt-sim/tests/regression/test_stage0_analytic.py
  - cwt-sim/tests/experiments/test_loop_at_hotspot_cli.py
  - .github/workflows/tests.yml
persona: implementer
authority: [read, write, test]
restricted: [cross-cutting-changes, modify-core-api]
---

# Research Experiments

## Overview

Gate-based research workflows organized by validation stage: stage0 (analytic sanity), gateA (parameter sweep), gateB (ridge finding), gateC (topology robustness), gateD (optional CHSH). Additional experiments (wilson_loop_3d, torus_plateau, inverse_design, etc.) target specific research questions. Each experiment has a `run.py` CLI entry point and co-located artifacts.

## Behavioral Directives

- **Must:** Ensure stage0 analytic checks pass before validating higher-gate experiments (GATE-001).
- **Must:** Write artifacts to the experiment's own `artifacts/` directory (GATE-002).
- **Must:** Make each experiment's `run.py` invokable as a standalone Typer CLI (GATE-003).
- **Must not:** Modify core CWT API from experiment code — report API gaps to orchestrator.
- **Always:** Include a REPORT.md summarizing findings when an experiment produces results.
- **Never:** Write experiment outputs to shared or root-level directories.

## Change Expectations

- Preserve the gate ordering convention (stage0 < gateA < gateB < gateC < gateD).
- Preserve existing experiment CLI interfaces.
- Preserve artifact isolation per experiment directory.

## Cross-Links

- **Parent directives:** `AGENTS.md`
- **Governing ADRs:** ADR-0001 (dynamics context), ADR-0003 (geometry context), ADR-0005 (gate progression)
- **Related components:** `cwt-sim/cwt/agents.md` (core API consumer), `cwt-sim/baselines/agents.md` (comparison targets)
- **Invariants:** See `.armature/invariants/registry.yaml` for entries: GATE-001, GATE-002, GATE-003
