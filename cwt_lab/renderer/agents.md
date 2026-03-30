---
scope: "cwt_lab/renderer"
governs: "React UI — phase dashboards, visualization components, experiment navigation"
inherits: "AGENTS.md"
adrs: [ADR-0002, ADR-0006]
invariants: [IPC-001, LAB-001, LAB-002, LAB-003]
enforced-by:
  - cwt_lab/renderer/components/__tests__/
  - cwt_lab/shared/__tests__/validators.test.ts
  - .github/workflows/cwt-lab-tests.yml
persona: implementer
authority: [read, write, test]
restricted: [cross-cutting-changes, modify-electron, spawn-processes]
---

# Renderer (React UI)

## Overview

React 18 frontend with Material-UI, phase-specific dashboard components (Phase1-5), Zustand state management, Plotly visualizations, and experiment navigation. Communicates with the Electron main process exclusively through the preload-exposed IPC API.

## Behavioral Directives

- **Must not:** Import from `electron/` or spawn child processes (IPC-001).
- **Must not:** Contain simulation parameter validation logic — use shared Zod schemas (LAB-001).
- **Must:** Use Zustand stores for cross-component state (LAB-002).
- **Must:** Support demo mode rendering without Python available (LAB-003).
- **Always:** Use the preload API (window.api) for all backend communication.
- **Never:** Access Node.js APIs directly from renderer code.

## Change Expectations

- Preserve the phase component structure (Phase1 through Phase5).
- Preserve Zustand store patterns in `store/`.
- Preserve demo mode functionality via DemoModeContext.
- Preserve the preload API contract surface.

## Cross-Links

- **Parent directives:** `AGENTS.md`
- **Governing ADRs:** ADR-0002 (IPC bridge), ADR-0006 (desktop lab architecture)
- **Related components:** `cwt_lab/electron/agents.md` (provides IPC backend), `cwt_lab/shared/agents.md` (provides Zod schemas)
- **Invariants:** See `.armature/invariants/registry.yaml` for entries: IPC-001, LAB-001, LAB-002, LAB-003
