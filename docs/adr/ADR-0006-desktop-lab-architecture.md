# ADR-0006: Desktop Lab Architecture

**Status:** Accepted
**Date:** 2026-03-30
**Supersedes:** N/A

## Context

Researchers need an interactive interface for configuring simulations, viewing results, and managing experiment runs without touching the CLI. The desktop lab must bridge the gap between the Python simulation backend and a rich visual frontend while remaining maintainable as a secondary deliverable alongside the core simulation code.

## Decision

The desktop lab is built as an Electron application in `cwt_lab/`:
- **electron/** — Main process with IPC handlers, runner infrastructure, and Python invocation.
- **renderer/** — React 18 UI with Material-UI, Zustand state management, and Plotly visualizations.
- **shared/** — Zod-validated type contracts shared between main and renderer processes.
- Built with electron-vite for fast dev iteration.
- Phase-specific components (Phase1Mapping, Phase2Features, Phase3Loops, Phase4Explorer3D, Phase5Optimize) mirror the gate progression.

## Consequences

- UI development is decoupled from simulation code — different testing strategies, different CI workflows.
- Zustand stores provide predictable state management without Redux boilerplate.
- Zod schemas in shared/ enforce type safety across the IPC boundary at runtime.
- Adding a new experiment view requires: a React component, a Zustand store slice (if stateful), and an IPC handler registration.

## Invariants

- **LAB-001:** Renderer components must not contain business logic for simulation parameter validation. All validation flows through shared/ Zod schemas.
- **LAB-002:** State management must use Zustand stores in `renderer/store/`. No component-local state for data that crosses component boundaries.
- **LAB-003:** The desktop lab must function in demo mode (without Python available) for UI development and testing.

## Non-Goals

- This ADR does not cover web deployment of the lab UI.
- This ADR does not mandate specific visualization library choices beyond Plotly.

## Observability

Electron main process logs IPC traffic volume and handler latency. Renderer performance metrics are available via React DevTools.

## Security Considerations

Electron's contextBridge is used to expose a minimal API surface to the renderer. Node integration is disabled in renderer windows.

## Acceptance Criteria

- [ ] Shared Zod schemas exist for all IPC message types.
- [ ] Demo mode renders all phase views without Python errors.
- [ ] No renderer component imports from `electron/` directly (all through preload API).
