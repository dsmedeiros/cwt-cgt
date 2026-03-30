# ADR-0002: IPC Bridge Pattern for Electron-Python Communication

**Status:** Accepted
**Date:** 2026-03-30
**Supersedes:** N/A

## Context

The desktop lab (cwt_lab) provides a React UI that must invoke Python CLI commands from cwt-sim and stream results back. A clean boundary between the Electron main process and the Python runtime is needed to prevent tight coupling, support environment detection, and enable graceful error handling when Python is unavailable.

## Decision

All Python invocation flows through an IPC bridge in `cwt_lab/electron/`:
- **runner/** module builds command arguments, manages process lifecycle, and parses stdout/stderr.
- **ipc.ts** registers Electron IPC handlers that the renderer calls via `preload.ts` exposed APIs.
- Environment detection uses progressive fallback: `.venv/bin/python` -> `python3` -> `python`.
- Each run gets a unique ID, timeout, and artifact collection path.
- Shared type contracts live in `cwt_lab/shared/` using Zod schemas for runtime validation.

## Consequences

- Renderer code never spawns processes directly — all execution goes through IPC handlers.
- Python environment issues surface at detection time, not mid-run.
- Adding a new experiment type requires: a Python CLI entry point, a command builder in runner/, and an IPC handler registration.
- Zod schemas in shared/ are the source of truth for request/response shapes.

## Invariants

- **IPC-001:** Renderer code must never import from `electron/` or spawn child processes. All Python interaction flows through IPC.
- **IPC-002:** Every IPC handler must validate inputs using shared Zod schemas before invoking Python.
- **IPC-003:** Python environment detection must use the progressive fallback chain. No hardcoded paths.
- **IPC-004:** Every Python invocation must have a configurable timeout. No unbounded waits.

## Non-Goals

- This ADR does not specify the Python CLI argument format (that is cwt-sim internal).
- This ADR does not cover the renderer component architecture.

## Observability

IPC handler invocations, Python process spawn/exit events, and timeout triggers are logged to the Electron main process console.

## Security Considerations

User-supplied parameters must be sanitized before shell invocation. The runner module uses argument arrays (not string concatenation) to prevent injection.

## Acceptance Criteria

- [ ] No renderer source file imports from `electron/` directly.
- [ ] All IPC handlers validate inputs with Zod before execution.
- [ ] Environment detection test covers all three fallback stages.
- [ ] Timeout test verifies process termination on expiry.
