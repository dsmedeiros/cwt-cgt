# Armature — Agentic Repository Management Architecture

**Version:** 1.0.0
**Status:** Active
**Author:** Dave Medeiros / Panoptic Systems

---

## 1. Purpose

Armature is a portable scaffold specification for standing up agentic repository governance. It defines the complete system — governance file hierarchy, agent persona architecture, invariant enforcement, and operational protocols — so that any new project can be initialized with a production-grade structure for human-directed, AI-executed development.

The methodology assumes AI coding agents are primary contributors. Every design choice optimizes for a world where agents must be steered with precision, constrained by explicit authority boundaries, and held accountable through auditable enforcement mechanisms.

Armature is not a framework or a library. It is a structural methodology encoded as files, conventions, and protocols. It degrades gracefully to human-readable documentation when agentic tooling is not active.

---

## 2. Design Principles

**P1 — Governance as Structure, Not Convention.**
Rules are encoded in files at the locations they govern. An agent working in `src/ledger/` reads `src/ledger/agents.md` — it does not rely on remembering a conversation or a monolithic config.

**P2 — Progressive Disclosure.**
An agent reads only what its current scope requires at the detail level it needs. The orchestrator reads frontmatter to plan. Implementers read their local scope to execute. The reviewer reads the registry to verify. Nobody reads everything. This preserves context for the work that matters.

**P3 — Authority Boundaries Over Skill Gradients.**
Agent personas are defined by what they can decide, not how smart they are. The orchestrator plans. Implementers execute within scope. The reviewer enforces invariants. Nobody has unchecked authority.

**P4 — Externalized Working Memory.**
Session state, review verdicts, escalation packages, and the governance journal live on disk, not in conversation context. The agentic workflow survives compaction, restarts, and context window limits.

**P5 — Defense in Depth.**
Critical invariants are stated in governance files, enforced by CI tests, validated by the reviewer persona, and checked by mechanical hooks. No single layer is trusted alone. Behavioral enforcement (persona directives) is the primary layer; mechanical enforcement (hooks, CI) is the backstop. Hooks can prevent a bad write, but they cannot reclaim the context spent reasoning about it.

**P6 — Inside/Outside Separation.**
The orchestrator sees the outside: topology, task graph, verdicts, governance. Implementers see the inside: code, tests, local constraints. The reviewer sees both through a compliance lens. These boundaries are never crossed. The orchestrator does not read source code. Implementers do not read peer scopes.

**P7 — Machine-Readable Governance.**
AGENTS.md frontmatter, the invariant registry, and session state files use structured formats. Agents parse them programmatically rather than extracting meaning from prose.

**P8 — Degraded Mode as Documentation.**
Every governance file is human-readable. When no agentic workflow is active, the scaffold serves as project documentation. No mechanism depends exclusively on agent tooling.

**P9 — YAGNI.**
The scaffold supports a single developer directing an agentic workflow. Multi-user, multi-session, and commercial distribution concerns are deferred until they are real.

---

## 3. Governance Layer

### 3.1 File Hierarchy

```
project-root/
├── CLAUDE.md                              ← Claude Code entry point / lean router
├── agents.md                              ← Root governance directives (cross-tool)
├── .armature/
│   ├── ARMATURE.md                        ← This specification
│   ├── config.yaml                        ← Project metadata and topology
│   ├── personas/
│   │   ├── orchestrator.md                ← Orchestrator persona
│   │   ├── reviewer.md                    ← Reviewer persona
│   │   ├── planner.md                     ← Opt-in planner persona
│   │   └── implementers/
│   │       └── {component}.md             ← Per-component implementer personas
│   ├── invariants/
│   │   ├── registry.yaml                  ← Machine-readable invariant index
│   │   └── invariants.md                  ← Human-readable constraint list
│   ├── templates/
│   │   ├── agents.md.tmpl                 ← AGENTS.md skeleton
│   │   ├── adr.md.tmpl                    ← ADR template
│   │   └── persona.md.tmpl               ← Implementer persona template
│   ├── journal.md                         ← Governance journal (gitignored, append-only)
│   ├── session/
│   │   ├── state.md                       ← Living session state
│   │   └── logs/                          ← Completed session logs
│   ├── reviews/                           ← Reviewer verdict artifacts
│   ├── escalations/                       ← Circuit breaker handoff packages
│   └── hooks/
│       └── post-stop.sh                   ← Mechanical contract validation
├── .claude/
│   ├── agents/
│   │   ├── reviewer.md                    ← Claude Code subagent → .armature/personas/reviewer.md
│   │   ├── planner.md                     ← Claude Code subagent → .armature/personas/planner.md
│   │   └── {component}-impl.md            ← Claude Code subagent → .armature/personas/implementers/{component}.md
│   └── commands/
│       ├── armature-init.md               ← Instantiation protocol
│       ├── armature-extend.md             ← Component onboarding
│       └── checkpoint.md                  ← Pre-compaction state save
├── docs/
│   └── adr/                               ← Architecture decision records
└── {project source tree}/
    ├── agents.md                          ← Scoped directives per directory
    └── ...
```

### 3.2 What Gets Committed vs. Gitignored

**Committed:**
- `CLAUDE.md`, root `agents.md`
- `.armature/ARMATURE.md`, `config.yaml`
- `.armature/personas/` (all persona files)
- `.armature/invariants/` (registry and invariants.md)
- `.armature/templates/`
- `.armature/hooks/`
- `.claude/agents/` (reviewer, planner, implementer subagents — not orchestrator)
- `.claude/commands/`
- `docs/adr/`
- All scoped `agents.md` files in the source tree
- `.taskmaster/tasks/` and `.taskmaster/config.json` (Taskmaster persistence)

**Gitignored:**
- `.armature/session/` (ephemeral working state)
- `.armature/reviews/` (ephemeral review artifacts)
- `.armature/escalations/` (ephemeral escalation packages)
- `.armature/journal.md` (governance journal — survives rollbacks by being unversioned)

### 3.3 CLAUDE.md — Orchestrator Entry Point and Lean Router

CLAUDE.md serves a dual role: it is the Claude Code entry point that survives compaction, and it establishes the main agent as the orchestrator by directive.

**The first lines of CLAUDE.md must:**
1. Direct the main agent to operate as the orchestrator: "You are the orchestrator. Read and follow `.armature/personas/orchestrator.md` as your operating protocol."
2. Instruct session recovery: "On session start, read `.armature/session/state.md` and `.armature/journal.md`. Query Taskmaster for current task status."
3. Explicitly list available Taskmaster MCP tools by name, ensuring tool access is scoped rather than inherited carte blanche.

**The remainder of CLAUDE.md serves as the lean router (constrained to ~200 lines):**

1. **System overview** — What this project is, in 2–3 paragraphs.
2. **Critical invariants** — The top 5–10 hardest constraints, pulled from the invariant registry.
3. **Routing table** — A map from task type to which files to read.
4. **Meta-instruction** — Directive to read scoped `agents.md` files before modifying directories. Commit protocol summary. Journal recovery directive.
5. **Agent workflow topology** — Brief description of the pipeline and personas with pointers to `.armature/personas/`.
6. **Quick reference** — Build, test, deploy commands.

**Why the orchestrator is the main agent, not a subagent:**
If the orchestrator were a subagent, the main agent would need to know to spawn it for every interaction — an unreliable routing step. More critically, subagents spawning subagents creates a three-level nesting problem where context gets summarized at each return boundary. With the orchestrator as the main agent, implementers, reviewers, and planners are one level deep — clean context boundaries, reliable delegation.

**CLAUDE.md must not:**
- Aggregate or summarize the contents of scoped `agents.md` files
- Duplicate ADR content
- Exceed ~200 lines (excluding the orchestrator directives at the top)
- Contain implementation details

CLAUDE.md fully survives compaction. After `/compact`, Claude Code re-reads it from disk. This is why it serves as both the orchestrator's identity anchor and the routing layer — it is the one document guaranteed to persist.

### 3.4 Root agents.md — Cross-Tool Governance

Root `agents.md` holds global directives applicable to any AI coding tool (Claude Code, Codex, future tooling). It defines:

- Repository-wide coding standards
- Cross-cutting architectural invariants
- ADR governance protocol (review ADRs before implementation)
- Testing expectations
- Documentation requirements
- Package management rules
- PR/commit conventions

Root `agents.md` does not reference Claude Code-specific features, personas, or Armature internals. It is tool-agnostic.

### 3.5 Scoped agents.md — The Cascading Hierarchy

Each major component directory contains its own `agents.md` using a consistent structure with machine-readable YAML frontmatter.

**Frontmatter Schema:**

```yaml
---
scope: src/ledger                          # Directory path this file governs
governs: "Brief description of responsibility"
inherits: src/agents.md                    # Parent agents.md (explicit chain)
adrs: [ADR-0002, ADR-0006]                # Governing ADRs for this scope
invariants: [SEQ-001, DIGEST-002]          # Invariant IDs from the registry
enforced-by:                               # CI/runtime enforcement for this scope
  - tests/ledger_sequence_test.go
  - src/ledger/failfast.go
persona: implementer                       # Agent persona type for this scope
authority: [read, write, test]             # Permitted actions
restricted: [cross-cutting-changes, schema-migration]  # Prohibited actions
---
```

**Body Structure (4 sections):**

1. **Overview** — What this component does, in 2–3 sentences.
2. **Behavioral Directives** — Non-negotiable rules for this scope. Use imperative language: "must," "must not," "always," "never."
3. **Change Expectations** — What must not change when modifying this component. Preservation rules.
4. **Cross-Links** — References to related ADRs, invariants, and other `agents.md` files.

**Inheritance Model:**

Scoped files inherit from their declared parent. The resolution order when an agent works in `src/ledger/`:

1. Read `CLAUDE.md` (always loaded)
2. Read root `agents.md` (global directives)
3. Read `src/agents.md` (source-level directives)
4. Read `src/ledger/agents.md` (component-level directives)

More specific files take precedence on implementation details. Invariants propagate downward unconditionally — a leaf `agents.md` can add constraints but cannot relax them. See §8 Conflict Resolution.

### 3.6 Architecture Decision Records (ADRs)

ADRs live in `docs/adr/` and function as behavioral specifications, not historical decision logs. Each ADR defines what was decided and the invariants that decision implies.

**Required ADR Sections:**

- Context — Why this decision was needed
- Decision — What was decided
- Consequences — What follows from the decision
- Invariants — Hard rules that implementation must follow (structured with IDs matching the registry)
- Non-Goals — What this ADR explicitly does not cover
- Acceptance Criteria — Objective checks that prove the decision is implemented

**ADR Governance Protocol (encoded in root agents.md):**

- Core architectural decisions must be captured as ADRs before implementation
- Contributors must review applicable ADRs at the start of every implementation effort
- PRs and commits must reference governing ADRs
- If no ADR exists for a core decision, create one first

### 3.7 Invariant Registry

`.armature/invariants/registry.yaml` is the machine-readable index of all hard constraints. Each entry maps an invariant to its definition source, enforcement mechanisms, and governance file references.

**Registry Entry Schema:**

```yaml
invariants:
  SEQ-001:
    name: "Sequence contiguity"
    severity: critical                     # critical | high | standard
    description: "Event sequences must be zero-based and contiguous per tenant"
    defined-in: docs/adr/0002-event-schema.md
    enforced-by:
      ci:
        - tests/ledger_sequence_test.go
      startup:
        - src/ledger/failfast.go
      runtime:
        - src/events/sequence_guard.go
    referenced-in:
      - agents.md
      - src/ledger/agents.md
      - src/binder/agents.md
      - src/events/agents.md
    exceptions: []                         # Any approved exceptions with rationale
```

**Registry Rules:**

- Every invariant must have a unique ID using the pattern `{CATEGORY}-{NNN}`
- Every invariant must trace to at least one ADR (`defined-in`)
- Every critical-severity invariant must have at least one CI enforcement (`enforced-by.ci`)
- Exceptions must include a rationale and reference a justifying ADR
- The registry is the source of truth for which invariants exist; `invariants.md` is the human-readable rendering

`.armature/invariants/invariants.md` is the human-readable companion — prose descriptions of each invariant grouped by category. It is generated from or manually kept in sync with the registry. In degraded mode (no agentic tooling), this is what a human reads.

### 3.8 ADR Relaxation

Pre-1.0 projects operate under reduced ADR ceremony:

- **Pre-1.0:** ADRs are recommended but not required for architectural decisions. The orchestrator may record decisions in the governance journal or session state instead of creating a formal ADR. This reduces overhead during early, high-churn development where architectural direction changes frequently.
- **Post-1.0:** ADRs are required for any change that touches invariants or cross-cutting concerns. Once a project reaches 1.0, its architectural surface is stable enough that formal decision records are worth the overhead.

The transition is triggered by the first `v1.0.0` tag. The orchestrator enforces the appropriate level of ceremony based on the project's version in `.armature/config.yaml`.

---

## 4. Persona Architecture

### 4.1 Overview

Armature defines four agent personas organized by decision authority, not skill level:

| Persona | Authority | Scope | Writes Code? | Agent Level |
|---|---|---|---|---|
| Orchestrator | Planning, delegation, acceptance | Global | No | Main agent |
| Implementer | Execution within declared scope | Per-component | Yes | Subagent |
| Reviewer | Invariant compliance, veto | Global (read-only) | No | Subagent |
| Planner | Step-by-step decomposition | Per-task (opt-in) | No | Subagent |

The orchestrator runs as the main Claude Code agent (established by directive in CLAUDE.md). Implementers, reviewers, and planners are subagents spawned by the orchestrator. This keeps the hierarchy to two levels maximum — clean context boundaries, no nesting problems.

Persona definitions live in `.armature/personas/`. Subagent wiring lives in `.claude/agents/` (for implementers, reviewers, and planners only — the orchestrator is not a subagent).

### 4.2 Orchestrator

**File:** `.armature/personas/orchestrator.md`
**Claude Code agent level:** Main agent (established by CLAUDE.md directive)

The orchestrator is the single point of contact between the human and the agentic workflow. The human talks to the orchestrator. The orchestrator handles everything else. The human should never need to write PRD files, run Taskmaster commands, invoke implementers, or interact with any other agent.

**The orchestrator's full pipeline:**

```
Conversation → PRD → Task Graph → Delegation → Review → Acceptance
```

**Phase A — Discovery and Requirements:**
- Conducts a requirements conversation with the human
- Asks clarifying questions to surface scope, constraints, dependencies, and acceptance criteria
- Generates the PRD and saves it to `.taskmaster/docs/` (the human never writes PRDs)
- Confirms the PRD with the human before proceeding

**Phase B — Milestone and Task Decomposition:**
- Decomposes the PRD into 5–10 milestones, each producing a working verifiable increment
- Parses the current milestone into Taskmaster tasks (not the whole PRD at once)
- Runs complexity analysis; flags tasks scoring > 7 for planner involvement
- Expands complex tasks into subtasks
- Annotates each task with its target agents.md scope
- Presents the milestone list and current milestone's task graph for confirmation
- Each milestone gets its own build candidate tag on completion

**Phase C — Execution:**
- Reads CLAUDE.md and AGENTS.md frontmatter for topology
- Queries Taskmaster for the next task respecting dependency order
- Writes delegation intent to session state before spawning implementers (auto-compaction safety)
- Delegates to scoped implementers based on AGENTS.md scoping
- Spawns the reviewer after each implementer completes
- On reviewer PASS: commits changes with structured message, updates Taskmaster
- On reviewer FAIL: re-delegates with verdict reference (max 3 cycles)
- On 3 failures: escalates to human, writes to journal
- Tags build candidates at milestone completion
- Maintains session state, governance journal, and Taskmaster state

**Mid-flight adaptation:** When the human changes direction, the orchestrator updates the PRD, revises affected Taskmaster tasks, updates governance files if needed, and confirms the revised plan before resuming.

**The orchestrator must not:**
- Write application code
- Bypass the reviewer
- Delegate cross-cutting changes to a single implementer
- Delegate two tasks to the same scope simultaneously
- Continue past the circuit breaker threshold (3 rejection cycles → escalate)

**Authority over governance files:**
- Can update CLAUDE.md (routing table, critical invariants)
- Can update root agents.md (global directives)
- Can update the invariant registry (new invariants, new references)
- Can create new scoped agents.md files (component onboarding)
- Can generate and update PRDs in `.taskmaster/docs/`
- Can log exceptions to invariants with rationale
- Can write to the governance journal
- Can commit accepted changes and tag build candidates

**Token and session discipline:**
- Read AGENTS.md frontmatter (YAML headers only) to build delegation plans
- Delegate minimum necessary context per implementer — reference specific ADRs listed in frontmatter, not "read all ADRs"
- Point each implementer at only the files listed in its scoped AGENTS.md frontmatter
- Do not read application source code — delegate exploration tasks instead
- Checkpoint proactively at milestone boundaries; prefer fresh sessions over extended runs

### 4.3 Implementer

**Template:** `.armature/personas/implementers/{component}.md`
**Claude Code subagent:** `.claude/agents/{component}-impl.md`

Implementer personas are created per-component during onboarding. Each is scoped to a single AGENTS.md boundary. An implementer:

- Reads its local AGENTS.md (frontmatter + body) and referenced ADRs
- Reads its persona file for behavioral characteristics
- Writes code, tests, and configs within its declared scope
- Cannot make cross-cutting changes or modify files outside its scope
- Cannot modify governance files (AGENTS.md, ADRs, registry)
- Reports back to the orchestrator: what changed, which files, which invariants were touched

**Dynamic scoping:**
The implementer's authority is defined by the `authority` and `restricted` fields in its scoped AGENTS.md frontmatter. The persona file provides the behavioral baseline (communication style, decision-making approach, error handling philosophy). The frontmatter provides the scope-specific boundaries.

**Circuit breaker awareness:**
If rejected by the reviewer, the implementer on re-delegation reads the structured verdict file at `.armature/reviews/{task-id}.md` before starting. It does not rely on conversational context from previous attempts. After 3 rejection cycles, the orchestrator escalates rather than re-delegating.

### 4.4 Reviewer

**File:** `.armature/personas/reviewer.md`
**Claude Code subagent:** `.claude/agents/reviewer.md`

The reviewer is an independent compliance checker with veto authority. It:

- Reads `.armature/invariants/registry.yaml` (the machine-readable constraint index)
- Reads `.armature/invariants/invariants.md` (human-readable context for ambiguous cases)
- Receives a changeset from the orchestrator (list of modified files, declared scope, invariants touched)
- Checks each claimed invariant against its enforcement mechanisms
- Validates that the changeset does not modify files outside the declared scope
- Validates that no invariant was relaxed without an approved exception
- Produces a structured verdict at `.armature/reviews/{task-id}.md`

**Verdict Format:**

```markdown
# Review Verdict: {task-id}

## Scope Compliance
- Declared scope: {scope from AGENTS.md frontmatter}
- Files modified: {list}
- Out-of-scope modifications: {list or "none"}

## Invariant Compliance
| Invariant | Status | Notes |
|---|---|---|
| SEQ-001 | PASS | Sequence contiguity preserved |
| DIGEST-002 | FAIL | Digest computation modified without updating canonical helper |

## Verdict: PASS | FAIL | CONDITIONAL
## Required Changes (if FAIL/CONDITIONAL):
- {specific remediation instructions}
```

**The reviewer must not:**
- Write or modify code
- Suggest implementation approaches (only identify violations)
- Override its own verdict
- Trigger rollback (it recommends; the orchestrator decides)

### 4.5 Planner (Opt-In)

**File:** `.armature/personas/planner.md`
**Claude Code subagent:** `.claude/agents/planner.md`

The planner is activated by the orchestrator when a task within a single scope is too complex for a single implementer pass. It:

- Reads the local AGENTS.md and referenced ADRs for the target scope
- Produces a numbered implementation plan with invariant checkpoints
- Identifies dependencies between steps
- Flags steps that require reviewer validation before proceeding
- Hands the plan to the implementer for execution

The orchestrator decides when to invoke the planner based on task complexity. Not every task requires planning — simple, well-scoped changes go directly to an implementer.

### 4.6 Subagent Spawning Protocol

Every subagent delegation follows a strict 4-step protocol. The orchestrator must not skip steps or combine them implicitly.

1. **Read the agent file.** Read the target persona's `agents.md` frontmatter (scope, invariants, ADRs, authority boundaries). For implementers, also read the persona file at `.armature/personas/implementers/{component}.md`.
2. **Compose the delegation prompt.** The prompt must explicitly include:
   - Task description and acceptance criteria
   - Scope boundary (which files/directories the agent may modify)
   - Applicable invariant IDs (from the agents.md frontmatter, not the full registry)
   - Deliverables expected (files changed, tests passing, artifacts produced)
   - Constraints (what the agent must not do, any prior reviewer feedback)
3. **Spawn via the Agent tool.** Use the appropriate `subagent_type` from `.claude/agents/`. Set `run_in_background` only when Bash permission is pre-approved and the task is independent.
4. **Collect and evaluate the result.** Read the agent's output. Verify it claims to have stayed in scope. Route the changeset to the reviewer.

This protocol prevents the orchestrator from writing code "temporarily" when composing a delegation feels like more work than just doing the task. If composing the delegation prompt is difficult, that is a signal the task needs further decomposition — not that the orchestrator should implement it directly.

---

## 5. Enforcement Model

### 5.1 In-Session Pipeline (Agentic)

```
Human ←→ Orchestrator → PRD → Taskmaster → [Planner?] → Implementer → Reviewer → Orchestrator
              ↑                                                                        ↓
              └──────────────────────── Accept / Reject / Escalate ────────────────────┘
```

**Phase A — Requirements:**
1. Human describes intent conversationally to the orchestrator
2. Orchestrator asks clarifying questions, confirms understanding
3. Orchestrator generates PRD, saves to `.taskmaster/docs/`, confirms with human

**Phase B — Planning (per milestone):**
4. Orchestrator decomposes PRD into milestones (5–10 working increments)
5. Orchestrator parses current milestone into Taskmaster tasks (via MCP `parse_prd` or `add_task`)
6. Orchestrator runs complexity analysis, expands complex tasks, annotates with scope
7. Orchestrator presents the plan to human for confirmation

**Phase C — Execution (per task):**
7. Orchestrator queries Taskmaster for next task
8. Orchestrator annotates task with target agents.md scope
9. If complexity > 7, orchestrator invokes planner first
10. Orchestrator writes delegation intent to session state (auto-compaction safety)
11. Orchestrator delegates to scoped implementer
12. Implementer executes, reports changeset
13. Orchestrator spawns reviewer against the changeset
14. Reviewer writes structured verdict to `.armature/reviews/{task-id}.md`
15. Orchestrator evaluates:
   - **PASS** → Commit with structured message, update Taskmaster, tag build candidate if milestone, write to journal if governance-relevant
   - **FAIL** → Re-delegate to implementer with verdict file reference (max 3 cycles)
   - **ESCALATE** → Write to `.armature/escalations/` and `.armature/journal.md`, surface to human

### 5.2 On-Stop Hooks (Mechanical)

Wired to Claude Code's `Stop` and `SubagentStop` lifecycle events. These run deterministic checks without LLM involvement:

- All modified files pass linting/formatting
- Contract tests for modified scopes pass
- Invariant registry is internally consistent (all references resolve)
- No uncommitted governance file changes exist without session log entries

**Hooks are the backstop, not the primary enforcement.** Hooks can prevent a bad write, but they cannot reclaim the context the agent spent reasoning about the bad write. The primary enforcement layer is the persona directive — "you do not write application code" — which prevents the reasoning from happening in the first place. Hooks catch what slips past the behavioral layer.

### 5.3 Scaffold Integrity Tests (CI)

A test suite that validates the governance structure itself:

- Every `agents.md` file referenced in CLAUDE.md's routing table exists
- Every ADR referenced in any `agents.md` frontmatter exists
- Every invariant ID in any `agents.md` frontmatter exists in the registry
- Every `enforced-by` entry in the registry points to a file that exists
- Every `referenced-in` entry in the registry points to a file that references that invariant
- CLAUDE.md routing table covers every `agents.md` file in the repo
- No `agents.md` file references a parent in `inherits` that doesn't exist
- No invariant has severity `critical` without at least one CI enforcement

### 5.4 CI Contract Tests (Project-Specific)

Implemented per-project in the test suite. These validate that architectural invariants are actually enforced at runtime:

- Schema validation tests (if applicable)
- Referential integrity tests (configs reference real entities)
- Startup fail-fast validation (services reject invalid configuration)
- Domain-specific invariant checks

### 5.5 Fast Path Pipeline

For tasks with complexity ≤ 3 (trivial changes, single-file fixes, documentation updates), the full pipeline is unnecessarily heavy. The fast path reduces ceremony while preserving the mandatory reviewer gate.

**Fast path flow:**
```
Human → Orchestrator → Implementer → Reviewer → Accept
```

**What is skipped:**
- PRD generation (the orchestrator creates a Taskmaster task directly from conversation)
- Planner invocation (complexity is below threshold)
- Milestone decomposition (single task, no milestone needed)

**What is NOT skipped:**
- Reviewer gate (mandatory, no exceptions)
- Structured commit message
- Session state update
- Governance journal entry (if governance-relevant)

**Eligibility criteria:**
- Task complexity ≤ 3 (as assessed by the orchestrator or Taskmaster's complexity analysis)
- Single implementer scope (task maps to exactly one agents.md boundary)
- No invariant ambiguity (all applicable invariants are clear)
- No cross-cutting changes

If any criterion is not met, the task follows the standard pipeline. The orchestrator makes the routing decision and records it in session state.

---

## 6. Resilience Mechanisms

### 6.1 Session State Protocol

The orchestrator maintains a living state file at `.armature/session/state.md` updated at every state transition — not after every message, but at every meaningful checkpoint.

**State transitions that trigger an update:**
- Task decomposed / Taskmaster updated
- Implementer delegated
- Implementer completed
- Reviewer verdict received
- Accept/reject/escalate decision made
- Build candidate tagged
- Rollback initiated
- New invariant or constraint discovered mid-session

**State File Structure:**

```markdown
# Armature Session State

## Current Objective
{high-level task from human}

## Build Candidate
{current build candidate tag, or "none"}

## Task Status
{Taskmaster task IDs with status: pending / delegated / complete / rejected / escalated}

## Active Delegation
{currently delegated task, implementer scope, start time}

## Pending Reviews
{tasks awaiting reviewer pass}

## Invariants Touched
{which invariants were relevant, any ambiguities found}

---
<!-- APPEND-ONLY BELOW THIS LINE -->

## Decisions Log
- {timestamp} — {decision with rationale, especially rejected approaches}
- {timestamp} — {decision}

## Discovered Context
- {timestamp} — {anything learned that isn't in agents.md or ADRs}
```

Sections above the append line are overwritten each update. Sections below are append-only — history matters for decisions and discoveries.

### 6.2 Checkpointing

The `/checkpoint` slash command is invoked before compaction or when the human wants to save state explicitly.

**Checkpoint protocol:**
1. Orchestrator updates `.armature/session/state.md` with full current status
2. Orchestrator syncs with Taskmaster (all task statuses current)
3. Orchestrator confirms the current build candidate tag
4. Human may safely run `/compact`

**Post-compaction recovery:**
CLAUDE.md is re-injected automatically by Claude Code. CLAUDE.md contains the directive: "At the start of any resumed or compacted session, read `.armature/session/state.md` if it exists. Resume from the recorded state."

### 6.3 Commit Protocol

After each reviewer PASS, the orchestrator commits the accepted changes immediately. Commits are per-task — do not batch across tasks.

**Commit message format:**
```
task-{id}: {task title}

Scope: {agents.md path}
Invariants: {invariant IDs touched}
Reviewer: PASS
```

Per-task commits ensure: work is preserved if auto-compaction kills the session, git history maps cleanly to the Taskmaster task graph, and rollback granularity is at the task level.

**Collision avoidance:** The orchestrator must never delegate two tasks to the same scope simultaneously. Parallel implementers must work on disjoint scopes (enforced by the reviewer's scope compliance check).

### 6.4 Build Candidates

A build candidate is a git tag representing a known-good milestone. Tags go on top of already-committed task work. The orchestrator tags a build candidate when:

- A milestone in the Taskmaster task graph completes (multiple accepted tasks)
- The human explicitly requests a snapshot

**Tag format:** `bc/{date}/{sequence}` — e.g., `bc/2026-03-13/001`

**Build candidate protocol:**
1. Orchestrator confirms all milestone tasks are committed and reviewer-PASS
2. Orchestrator runs `git tag bc/{date}/{sequence}`
3. Orchestrator records the tag in session state and the governance journal

**Rollback protocol:**
If a subsequent task introduces a regression or the reviewer recommends rollback:
1. Orchestrator writes rollback decision and rationale to the governance journal
2. Orchestrator executes `git reset --hard {build-candidate-tag}`
3. Orchestrator updates session state and Taskmaster
4. Orchestrator reads governance journal to identify any governance changes lost in the rollback
5. If governance changes need re-application (e.g., a component was onboarded as part of the rolled-back work but the architectural decision still stands), orchestrator re-applies them

**Rollback is an orchestrator-only action.** The reviewer can recommend it. Implementers cannot trigger it.

**Governance file rollback:** Committed governance files (agents.md, ADRs, registry entries) roll back with the code — this is correct for code-coupled governance. The governance journal is gitignored and survives rollback, providing the institutional memory needed to determine whether rolled-back governance changes should be re-applied.

### 6.5 Governance Journal

`.armature/journal.md` is an append-only, gitignored log of governance-relevant events. It provides institutional memory that survives code-level rollbacks, session boundaries, and compaction.

**The orchestrator writes to the journal when:**
- An invariant exception is approved (with rationale and ADR reference)
- An escalation is created or resolved
- An invariant ambiguity is discovered or resolved
- An ADR is created or amended
- An agents.md is created or modified
- A component is onboarded
- A build candidate is tagged
- A rollback is executed (from what tag, to what tag, what was lost)

**Journal entry format:**
```markdown
### {YYYY-MM-DD HH:MM} — {category}
{Description of what happened and why.}
```

**On cold start,** the orchestrator reads the journal to understand governance history. If a rollback occurred since the last session, the journal identifies what governance changes were lost and whether they need re-application.

The journal is not a replacement for session state (which tracks in-flight work) or the invariant registry (which tracks active constraints). It is the historical record that gives context to decisions.

### 6.6 Circuit Breaker

If an implementer is rejected 3 times on the same task, the orchestrator stops and escalates:

1. Writes accumulated review verdicts and implementation state to `.armature/escalations/{task-id}/`
2. Writes the escalation to `.armature/journal.md`
3. Updates Taskmaster task status to "escalated"
4. Updates session state
5. Surfaces the escalation to the human with a structured handoff:
   - What was attempted
   - Why it was rejected each time
   - What the unresolved tension is
   - Suggested resolution paths

**Three cycles is the hard limit.** More spinning almost never helps. Either the invariants are ambiguous, the decomposition was wrong, or there's a design tension requiring human judgment.

**Escalation recovery:** When the human resolves an escalation and tells the orchestrator what was decided, the orchestrator writes the resolution to the journal, clears the escalation directory, applies any governance changes that follow from the resolution, and resumes execution from the resolved task.

### 6.7 Cold Start vs. Warm Start

**Warm start (post-compaction):**
CLAUDE.md reloads (re-establishing orchestrator identity) → orchestrator reads `.armature/session/state.md` → reads `.armature/journal.md` for governance history → queries Taskmaster for task status → resumes from recorded state.

**Cold start (new session):**
1. Orchestrator reads CLAUDE.md (identity + orientation)
2. Reads `.armature/journal.md` for governance history
3. Checks for existing `.armature/session/state.md`:
   - If none exists → fresh session, proceed normally
   - If one exists → check if it's from an abandoned session
4. Checks for unresolved escalations in `.armature/escalations/`
5. Checks that working tree is clean relative to the last build candidate
6. If dirty state detected → surface to human before starting new work
7. Queries Taskmaster for any pending/in-progress tasks

### 6.8 Taskmaster Integration

Taskmaster (npm: `task-master-ai`) serves as the orchestrator's persistent task graph. It runs as an MCP server within Claude Code, giving the orchestrator direct tool access to task management without switching context.

**Setup (one-time per machine + per project):**

Global install:
```bash
npm install -g task-master-ai
```

Register MCP server with Claude Code:
```bash
claude mcp add-json "task-master" '{"command":"npx","args":["-y","task-master-ai"],"env":{"MODEL":"claude-code"}}'
```

Initialize per project:
```bash
task-master init
```

Configure `.taskmaster/config.json` to use Claude Code's built-in models (no external API keys required):
```json
{
  "models": {
    "main": { "provider": "claude-code", "modelId": "sonnet" },
    "research": { "provider": "claude-code", "modelId": "opus" },
    "fallback": { "provider": "claude-code", "modelId": "sonnet" }
  }
}
```

**What Taskmaster provides:**

- Persistent task graph on disk (`.taskmaster/tasks/`) — survives compaction inherently
- Dependency tracking between tasks — the orchestrator queries "next task" respecting dependency order
- Task complexity analysis — tasks scoring above 7 should be routed through the planner persona before delegation
- Subtask decomposition — complex tasks broken into manageable units
- PRD parsing — transforms a product requirements document into a structured task graph during `/armature-init`
- Cold start recovery — a new session reads Taskmaster state to understand what's pending/complete

**What Taskmaster does NOT provide (Armature session state covers these):**

- Which invariants were touched per task
- Reviewer verdicts and accept/reject decisions
- Build candidate tag tracking
- Governance file change log
- Discovered context and decisions rationale
- Conflict resolution and exception logging

**Orchestrator's Taskmaster workflow:**

The human never interacts with Taskmaster directly. The orchestrator manages the full pipeline:

1. Have a requirements conversation with the human
2. Generate the PRD from the conversation, save to `.taskmaster/docs/`
3. Confirm the PRD with the human
4. Parse the PRD into Taskmaster tasks via `parse_prd`
5. Run complexity analysis via `analyze_project_complexity`
6. Expand complex tasks (> 7) via `expand_task`
7. Present the task graph to the human for confirmation
8. Query Taskmaster for the next task via `next_task`
9. If complexity > 7, invoke the planner persona first
10. Delegate task to scoped implementer
11. On cycle completion: update Taskmaster via `set_task_status` (complete / blocked / escalated)
12. Tag build candidate on milestone task completion
13. Loop from step 8 until all tasks complete or human redirects
14. On `/checkpoint`, ensure all Taskmaster statuses are current

For small, well-scoped work that doesn't warrant a PRD, the orchestrator can create tasks directly via `add_task` from conversation.

When the human changes direction mid-flight, the orchestrator updates affected tasks, adds/removes tasks, and confirms the revised plan — all through Taskmaster's MCP tools.

**Recommended:** Commit `.taskmaster/tasks/` to version control. This provides persistence across sessions and rollback safety via build candidate tags.

### 6.9 Taskmaster Fallback Protocol

When the Taskmaster MCP server is unavailable (not installed, MCP connection fails, or tools do not respond), the orchestrator decomposes and tracks tasks inline using the same structural schema.

**Fallback task schema:**

```yaml
- id: {integer}
  title: "{task title}"
  description: "{task description}"
  dependencies: [{list of task IDs}]
  status: pending | in_progress | done | blocked | escalated
  scope: "{agents.md path}"
  complexity: {1-10}
```

**Fallback behavior:**
- The orchestrator writes the task graph to `.armature/session/state.md` under a `## Task Graph (Inline)` section
- Dependency resolution, status tracking, and complexity assessment are performed by the orchestrator directly
- The same delegation, review, and acceptance protocols apply — only the storage backend changes
- When Taskmaster becomes available again, the orchestrator migrates inline tasks to Taskmaster via `add_task`

**Purpose:** This ensures Armature functions as a self-contained governance system without hard external tooling dependencies. Taskmaster is the preferred backend, but its absence must not block work.

---

## 7. Operational Protocols

### 7.1 Instantiation — `/armature-init`

Armature instantiation is a three-phase process that works for both greenfield and existing repositories.

**Phase 0 — Pre-Flight (existing repos):**
The orchestrator scans the codebase before engaging the human:
- Reads directory tree, package manifests, configs, CI files, READMEs, existing tests
- Checks for existing governance artifacts (CLAUDE.md, agents.md, ADRs, .claude/, .taskmaster/)
- Tags the pre-Armature baseline: `git tag armature/pre-init`
- Reports findings to the human: what exists, what will be created, what will be incorporated

For greenfield repos, Phase 0 is minimal — just confirm the repo is initialized and tag the baseline.

**Phase 1 — Project Discovery:**
The orchestrator combines code analysis (from Phase 0) with a conversation with the human. For existing repos, the orchestrator leads with what it observed and asks the human to correct and extend. For greenfield repos, the orchestrator has a natural dialogue to surface requirements.

Discovery produces:
- `.armature/config.yaml` — project metadata and topology
- `.taskmaster/docs/prd.txt` — initial PRD generated from the conversation

Both are confirmed with the human before proceeding.

**Phase 2 — Scaffolding:**
Using discovery output, the system creates (checking for existing artifacts at each step):
1. Seed ADRs in `docs/adr/` — adopting existing ADRs, creating new ones for undocumented decisions
2. Invariant registry — scanning existing tests/guards for enforcement, marking gaps as TODOs
3. Human-readable invariants
4. Scoped `agents.md` files — merging with existing agents.md content where present
5. Implementer persona files
6. Claude Code subagent files (implementers, reviewer, planner — not orchestrator)
7. CLAUDE.md — merging with existing content, or generating fresh with orchestrator directive
8. `.gitignore` entries (appended, not replaced)
9. Taskmaster initialization (skipped if `.taskmaster/` exists)
10. Verification with human, initial build candidate tag, journal entry

**Ordering matters:** ADRs before registry (invariants reference ADRs) → registry before scoped agents.md (frontmatter references invariants) → agents.md before CLAUDE.md (routing table references agents.md files).

The full step-by-step protocol is defined in `.claude/commands/armature-init.md`.

### 7.2 Component Onboarding — `/armature-extend`

Triggered by the orchestrator when a new component directory is needed.

**Protocol:**
1. Orchestrator determines the new component's path, responsibility, and governing ADRs
2. Creates the directory
3. Creates `agents.md` with frontmatter (inherits, adrs, invariants, persona, authority, restricted)
4. Creates implementer persona file at `.armature/personas/implementers/{component}.md`
5. Creates Claude Code subagent at `.claude/agents/{component}-impl.md`
6. Updates invariant registry if new invariants apply
7. Updates CLAUDE.md routing table with new entry
8. Logs the onboarding in session state decisions log

**Component onboarding is an orchestrator-only action.** If an implementer discovers that a new component is needed, it reports that finding to the orchestrator.

### 7.3 Agentic Session Logging

Every orchestrator session produces a structured log at `.armature/session/logs/{session-id}.md` upon session completion:

```markdown
# Session Log: {session-id}
**Date:** {date}
**Objective:** {high-level task}
**Build Candidates Tagged:** {list of tags}

## Tasks Executed
| Task | Implementer Scope | Reviewer Verdict | Cycles | Outcome |
|---|---|---|---|---|
| {task} | {scope} | PASS/FAIL | {n} | accepted/escalated |

## Invariants Touched
{list of invariant IDs with any ambiguities noted}

## Decisions Made
{timestamped decisions with rationale}

## Discovered Context
{anything learned that should be considered for governance updates}

## Governance Changes
{any agents.md, ADR, registry, or CLAUDE.md modifications made during session}
```

Session logs are gitignored by default but can be committed if audit trail is desired.

### 7.4 Conflict Resolution

**Inheritance conflicts:**
More specific `agents.md` files take precedence on implementation details. Invariants propagate downward unconditionally.

**Rules:**
- A leaf `agents.md` can add constraints but cannot relax constraints defined in a parent
- A leaf `agents.md` can specify implementation approaches that differ from parent guidance
- If a genuine exception to an invariant is needed:
  1. The exception must be logged by the orchestrator with a rationale
  2. The exception must be recorded in the invariant registry under the `exceptions` field
  3. The exception must reference a justifying ADR
  4. The exception is visible to the reviewer, who validates the justification

**No silent relaxation.** An agent cannot ignore an invariant because a local `agents.md` doesn't mention it. Invariants apply globally unless explicitly excepted.

### 7.5 Token Budget and Session Discipline

Encoded in persona definitions, not enforced mechanically:

**Orchestrator:**
- Read AGENTS.md frontmatter (YAML headers only) to build delegation plans — do not read full bodies until needed
- Delegate minimum necessary context per implementer
- Reference specific ADRs from frontmatter, not "all ADRs"
- Do not read application source code — delegate exploration tasks instead
- If reasoning about implementation details instead of delegation strategy, stop and delegate

**Implementer:**
- Read only: local agents.md, referenced ADRs (from frontmatter), persona file
- Do not read peer agents.md files, invariant registry, or session state

**Reviewer:**
- Read only: invariant registry entries for touched invariants, relevant agents.md frontmatter for scope validation
- Do not read ADRs unless an ambiguity in the registry requires rationale lookup

**Planner:**
- Read only: local agents.md, referenced ADRs
- Produce plans, not implementations — keep output concise

**Session management:**
- Checkpoint proactively at every milestone completion, not just when requested
- Extended sessions accumulate invisible state that degrades performance. Prefer fresh sessions at milestone boundaries: checkpoint, compact, and resume.
- Do not run a single orchestrator session through an entire project. Milestone boundaries are natural session boundaries.

---

## 8. Schemas

### 8.1 .armature/config.yaml

```yaml
project:
  name: ""
  description: ""
  domain: ""

stack:
  languages: []
  frameworks: []
  databases: []
  infrastructure: []
  ci: ""

topology:
  # Component declarations — each becomes a scoped agents.md
  components:
    - path: src/component-a
      responsibility: ""
      adrs: []
    - path: src/component-b
      responsibility: ""
      adrs: []

governance:
  build-candidate-prefix: "bc"
  circuit-breaker-threshold: 3
  reviewer-required: true
```

### 8.2 AGENTS.md Frontmatter

```yaml
---
scope: ""                    # Directory path this file governs
governs: ""                  # Brief description of responsibility
inherits: ""                 # Parent agents.md path
adrs: []                     # List of governing ADR identifiers
invariants: []               # List of invariant IDs from registry
enforced-by: []              # CI/runtime enforcement files
persona: implementer         # Persona type: implementer
authority: []                # Permitted actions: read, write, test, deploy
restricted: []               # Prohibited actions
---
```

### 8.3 Invariant Registry Entry

```yaml
{CATEGORY}-{NNN}:
  name: ""
  severity: critical | high | standard
  description: ""
  defined-in: ""             # ADR path
  enforced-by:
    ci: []                   # Test file paths
    startup: []              # Fail-fast guard paths
    runtime: []              # Runtime guard paths
  referenced-in: []          # agents.md and other governance file paths
  exceptions: []             # Approved exceptions with rationale and ADR reference
```

---

## 9. Degraded Mode

When no agentic workflow is active, the Armature scaffold serves as project documentation:

- `CLAUDE.md` → project overview and navigation guide
- `agents.md` files → scoped development guidelines (YAML frontmatter is metadata; body is readable prose)
- `docs/adr/` → architectural decisions with rationale
- `.armature/invariants/invariants.md` → hard constraints in plain English
- `.armature/personas/` → role descriptions that double as team structure documentation

No governance mechanism depends exclusively on agent tooling. Every file is human-readable and useful without Armature's agentic workflow running.

---

## 10. Future Considerations (Deferred)

The following are explicitly deferred under the YAGNI principle:

- **Multi-user session isolation** — concurrent agentic sessions by different developers
- **Scaffold methodology versioning** — migration paths between Armature versions
- **Visual dependency graph generation** — from frontmatter cross-links
- **Automated CLAUDE.md routing table generation** — from agents.md file discovery
- **Automated invariant registry validation** — contract test that validates registry against reality
- **Commercial distribution** — packaging Armature for other teams/organizations

These are acknowledged as valuable and designed-for (the structured frontmatter enables most of them), but not implemented until the need is real.
