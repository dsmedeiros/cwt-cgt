# Invariants

Hard rules extracted from ADRs. Violations block commits via reviewer gate.

---

## Armature Governance

| ID | Severity | Rule | Rationale | Enforcement |
|---|---|---|---|---|
| SPEC-001 | critical | ARMATURE.md must be internally consistent — no broken cross-references or contradictory schema definitions | Specification integrity underpins all governance | `post-stop.sh` |
| SPEC-002 | high | Framework-generic files must stay in sync with canonical Armature repo | Prevents governance drift across backports | `post-stop.sh` |
| SCHEMA-001 | high | config.yaml must conform to schema in ARMATURE.md | Ensures machine-readable governance metadata is complete | `post-stop.sh` |
| SCHEMA-002 | high | Registry entries must have all required fields (id, name, severity, description, rule, defined-in, enforced-by, referenced-in, status) | Enables automated invariant verification | `post-stop.sh` |
| ADAPTER-001 | high | Tool-specific adapter files (e.g. CLAUDE.md, CODEX.md) must route to the same governance sources and must not redefine or contradict root/scoped governance, ADRs, or the invariant registry | Keeps multiple agent tools aligned on a single governance truth | Manual review |
| REF-001 | high | All `agents.md` paths referenced in `CLAUDE.md` routing table must resolve to files on disk | Prevents stale routing that silently bypasses scoped governance | `post-stop.sh` |
| REF-002 | high | All ADR references in `agents.md` frontmatter must resolve to files in `docs/adr/` | Keeps invariant provenance auditable | `post-stop.sh` |
| REF-003 | high | All `agents.md` paths referenced in `CODEX.md` routing table must resolve to files on disk | Same as REF-001 for the Codex adapter | `post-stop.sh` |
| DISCIPLINE-001 | high | Persona discipline tags declared in `agents.md` frontmatter must be defined in the standards corpus | Discipline references must be resolvable for reviewer to load the correct rules | Orchestrator protocol (no script) |

## Armature Hooks

| ID | Severity | Rule | Rationale | Enforcement |
|---|---|---|---|---|
| HOOK-001 | critical | The `block-dangerous-commands.sh` hook must block destructive shell commands on PreToolUse(Bash) events | Fail-closed guard against accidental data loss | `block-dangerous-commands.sh` |
| HOOK-002 | critical | The `block-config-changes.sh` hook must block agent-initiated configuration changes on ConfigChange events | Fail-closed guard against silent governance drift | `block-config-changes.sh` |
| HOOK-003 | high | Application code changes must be tracked for conditional test verification | Lets CI-001 skip cleanly when no app code is dirty | `mark-dirty.sh`, `post-stop.sh` |
| HOOK-004 | high | Subagents must receive governance context at spawn time | Subagents inherit invariants and routing rules from the orchestrator | `inject-context.sh` |
| HOOK-005 | high | Session state must be re-injected after context compaction | Preserves orchestrator identity across `/compact` | `reinject-context.sh` |
| HOOK-006 | medium | Agents should be advised of required reading before editing governed files | Prevents accidental edits to invariant-bearing files | `check-required-reading.sh` |

## SDLC Gates

| ID | Severity | Rule | Rationale | Enforcement |
|---|---|---|---|---|
| TDD-001 | high | Source file edits require a matching test file to exist | Test-first discipline at the edit boundary | `tdd-gate.sh` |
| PHASE-001 | high | Edits must be permitted by the current SDLC phase | Phase declares allowed file scope | `phase-gate.sh` |
| TIER0-001 | high | `DOMAIN.md` and `PROJECT.md` must exist at repo root | Tier-0 onboarding prerequisites for orchestrator routing | `tier0-preflight.sh` |
| HOTFIX-001 | critical | Hotfix bypass must produce an audit record and block subsequent normal-phase work until postmortem lands | Hotfix is a privileged escape valve; every use is logged | `hotfix-audit.sh` (planned) |
| CI-001 | high | Full CI pipeline (tests + types + lint + invariants) must run on Stop when code is dirty | Prevents ungated code from closing a session | `run-ci.sh` |

## Task Lifecycle

| ID | Severity | Rule | Rationale | Enforcement |
|---|---|---|---|---|
| TASK-001 | high | Tasks must have acceptance criteria before delegation | Reviewer needs concrete criteria to evaluate against | `task-readiness.sh` |
| TASK-002 | high | Deliverables must be auto-verified against acceptance criteria on SubagentStop | Catches silent under-delivery before orchestrator accepts | `task-completion.sh` |
| TASK-003 | high | Reviewer and (when triggered) red team must auto-fire on SubagentStop | Ensures every delegated change passes governance review | `auto-reviewer.sh` |

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
