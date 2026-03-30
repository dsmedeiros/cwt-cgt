---
scope: "cwt_lab/electron"
governs: "Electron main process — IPC bridge, Python invocation, run management, environment detection"
inherits: "AGENTS.md"
adrs: [ADR-0002, ADR-0006]
invariants: [IPC-001, IPC-002, IPC-003, IPC-004]
enforced-by:
  - cwt_lab/electron/__tests__/ipc.artifacts.test.ts
  - cwt_lab/electron/runner/__tests__/env.sanitize.test.ts
  - cwt_lab/electron/runner/__tests__/runManager.integration.test.ts
  - .github/workflows/cwt-lab-tests.yml
persona: implementer
authority: [read, write, test]
restricted: [cross-cutting-changes, modify-renderer]
---

# Electron Main Process

## Overview

The Electron main process layer: IPC handler registration, Python CLI invocation via the runner module, environment detection with progressive fallback, and run lifecycle management. This is the bridge between the React renderer and the Python simulation backend.

## Behavioral Directives

- **Must:** Validate all IPC inputs with shared Zod schemas before invoking Python (IPC-002).
- **Must:** Use progressive fallback for Python detection: .venv -> python3 -> python (IPC-003).
- **Must:** Set configurable timeouts on all Python invocations (IPC-004).
- **Must not:** Expose Node APIs to renderer beyond the preload contextBridge.
- **Always:** Use argument arrays (not string concatenation) for Python process spawning.
- **Never:** Hardcode Python paths or skip environment detection.

## Change Expectations

- Preserve the IPC handler registration pattern in `ipc.ts`.
- Preserve the runner module's argument builder / parser separation.
- Preserve the preload API surface — renderer depends on its shape.

## Cross-Links

- **Parent directives:** `AGENTS.md`
- **Governing ADRs:** ADR-0002 (IPC bridge), ADR-0006 (desktop lab architecture)
- **Related components:** `cwt_lab/renderer/agents.md` (consumer of IPC API), `cwt_lab/shared/agents.md` (Zod schema source)
- **Invariants:** See `.armature/invariants/registry.yaml` for entries: IPC-001, IPC-002, IPC-003, IPC-004
