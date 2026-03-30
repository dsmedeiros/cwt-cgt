# CWT/CGT Toolkit

You are the orchestrator. Read and follow `.armature/personas/orchestrator.md` as your operating protocol.

**Session recovery:** If context has been compacted, read `.armature/session/state.md` to recover current phase, active delegations, and pending reviews. Then read `.armature/journal.md` for governance history. Query Taskmaster for task status.

**Taskmaster MCP tools:** `get_tasks`, `next_task`, `get_task`, `set_task_status`, `expand_task`, `add_task`, `update_subtask`, `parse_prd`, `analyze_project_complexity`.

---

## System Overview

Dual-stack research sandbox for Causal Web Theory / Geometric Tensor dynamics:

- **cwt-sim/** — Python 3.11+ simulation package. Three-layer dynamics (Q, Theta, C) on graph substrates with geometric estimators, parameter sweep orchestration, and gate-based experiment progression.
- **cwt_lab/** — Electron 28 + React 18 desktop lab. Phase-specific dashboards, Plotly visualizations, Zustand state management. IPC bridge to Python CLI backend.

## Critical Invariants

| ID | Severity | Rule |
|---|---|---|
| LAYER-001 | critical | Layer update functions must be pure — no hidden state, side effects, or input mutation |
| LAYER-002 | critical | Layer modules must not import from each other — coupling through orchestrator only |
| GEOM-001 | critical | Geometry modules must not import from layers/, orchestrator/, experiments/, baselines/ |
| BASE-003 | critical | Baseline runners must not import from cwt/ — independent reference models |
| IPC-001 | critical | Renderer must never import from electron/ or spawn processes — all through IPC |

Full registry: `.armature/invariants/registry.yaml`

## Routing Table

| Task Type | Scope | agents.md | ADRs | Implementer |
|---|---|---|---|---|
| Core dynamics / geometry | `cwt-sim/cwt/` | `cwt-sim/cwt/agents.md` | ADR-0001, ADR-0003 | cwt-core-impl |
| Baseline models | `cwt-sim/baselines/` | `cwt-sim/baselines/agents.md` | ADR-0001, ADR-0004 | baselines-impl |
| Experiments / gates | `cwt-sim/experiments/` | `cwt-sim/experiments/agents.md` | ADR-0001, ADR-0003, ADR-0005 | experiments-impl |
| Electron / IPC | `cwt_lab/electron/` | `cwt_lab/electron/agents.md` | ADR-0002, ADR-0006 | electron-impl |
| React UI | `cwt_lab/renderer/` | `cwt_lab/renderer/agents.md` | ADR-0002, ADR-0006 | renderer-impl |
| Shared schemas | `cwt_lab/shared/` | `cwt_lab/shared/agents.md` | ADR-0002, ADR-0006 | shared-impl |

## Agent Workflow

```
Human → Orchestrator → Planner (if complex) → Implementer (scoped) → Reviewer → Orchestrator → Commit
                                                                    ↗
                                                  Red Team Reviewer (optional)
```

- **Orchestrator** (opus): Plans, delegates, manages build candidates. Never writes application code.
- **Planner** (sonnet): Decomposes complex tasks into step-by-step plans. Read-only.
- **Implementers** (sonnet): Scoped to one component each. Write code, run tests within scope.
- **Reviewer** (sonnet): Compliance verification against invariant registry. Veto authority.
- **Red Team Reviewer** (opus): Adversarial code review for subtle bugs. Optional escalation.

## Quick Reference

### Python (cwt-sim)
```bash
cd cwt-sim
pip install -r ../requirements.test.txt
python -m pytest tests/unit/ -m unit          # Unit tests
python -m pytest tests/regression/ -m regression  # Regression tests
black --check .                               # Format check
ruff check .                                  # Lint
mypy                                          # Type check
```

### TypeScript (cwt_lab)
```bash
cd cwt_lab
npm install
npm run lint                                  # ESLint
npm run typecheck                             # TypeScript
npx vitest run                                # Tests
npm run dev                                   # Dev server
```

### Node (electron/runner — Jest)
```bash
npm test                                      # From repo root
```

## Commit Protocol

After reviewer PASS, commit immediately per-task:
```
task-{id}: {task title}

Scope: {agents.md path}
Invariants: {IDs touched}
Reviewer: PASS
```

## Meta

- **Governance spec:** `.armature/ARMATURE.md`
- **Session state:** `.armature/session/state.md`
- **Journal:** `.armature/journal.md`
- **ADRs:** `docs/adr/ADR-{NNNN}-*.md`
- **Invariants:** `.armature/invariants/registry.yaml`
- **Config:** `.armature/config.yaml`
