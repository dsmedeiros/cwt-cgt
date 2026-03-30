---
scope: "."
governs: "Repository-wide development standards, cross-cutting invariants, and Armature governance"
inherits: null
adrs: [ADR-0001, ADR-0002, ADR-0003, ADR-0004, ADR-0005, ADR-0006]
invariants: [LAYER-001, LAYER-002, GEOM-001, BASE-003, IPC-001]
enforced-by:
  - .github/workflows/tests.yml
  - .github/workflows/cwt-lab-tests.yml
  - .armature/hooks/post-stop.sh
persona: orchestrator
authority: [read, plan, delegate, review]
restricted: [write-application-code]
---

# CWT/CGT Toolkit — Root Directives

## Overview

Dual-stack research toolkit: Python simulation package (`cwt-sim/`) for Causal Web Theory / Geometric Tensor dynamics, paired with an Electron/React desktop lab (`cwt_lab/`) for interactive exploration. Development spans both stacks with shared governance.

## Behavioral Directives

- **Must:** Follow the Armature governance workflow — all changes route through orchestrator, implementer, reviewer pipeline.
- **Must:** Run `black --check cwt-sim` and `ruff check .` before committing Python changes.
- **Must:** Run `npm --prefix cwt_lab run lint` and `npm --prefix cwt_lab run typecheck` before committing TypeScript changes.
- **Must not:** Commit changes that break existing tests in either stack.
- **Always:** Install dependencies from `requirements.test.txt` before running Python tests.
- **Always:** Prefer modular, clean code with single responsibility.
- **Never:** Merge cross-cutting changes without orchestrator approval.
- **Never:** Modify governance files (ADRs, agents.md, invariant registry) from implementer scope.

## Change Expectations

- Preserve the import boundary between cwt-sim/ and cwt_lab/ — no Python package imports TypeScript, no TypeScript imports Python modules.
- Preserve the CI pipeline — both workflow files must pass on all PRs.
- Preserve the Armature scaffold structure under `.armature/`.

## Cross-Links

- **Scoped directives:** `cwt-sim/cwt/agents.md`, `cwt-sim/baselines/agents.md`, `cwt-sim/experiments/agents.md`, `cwt_lab/electron/agents.md`, `cwt_lab/renderer/agents.md`, `cwt_lab/shared/agents.md`
- **Governing ADRs:** All 6 ADRs in `docs/adr/`
- **Invariant registry:** `.armature/invariants/registry.yaml`
