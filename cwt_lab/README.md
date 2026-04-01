# CWT Lab Developer Guide

**Author:** Dave Medeiros / Panoptic Systems

CWT Lab is the Electron + React companion UI for the CWT calibration toolkit. This document captures the
engineering workflows for installing dependencies, running the desktop shell during development, packaging
for distribution, and extending the command catalogue.

## Installation

1. Install the shared Node.js dependencies from the repository root:

   ```bash
   npm install
   ```

2. Install the Electron workspace dependencies:

   ```bash
   npm --prefix cwt_lab install
   ```

3. Provision a Python environment that can import the `cwt` package as well as the `experiments` module from
   `cwt-sim`. The default development flow expects a virtual environment located at `.venv/` under the repo
   root. Activate it and install simulation requirements:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   pip install -r requirements.test.txt
   ```

   The run manager automatically injects the `cwt-sim` directory into `PYTHONPATH` for every launched
   calibration job.

## Running the desktop shell locally

Start the renderer + Electron process with hot-module reloading:

```bash
npm --prefix cwt_lab run dev
```

Electron-Vite will launch the renderer on port `5173` and start the Electron host pointed at the compiled
entrypoints. The preload script exposes the `window.CWT` API used throughout the React application.

## Packaging builds

To build a production bundle, run:

```bash
npm --prefix cwt_lab run dist
```

Electron Builder produces OS-specific artifacts inside `cwt_lab/dist/`. To inspect an unpacked directory for
manual testing, run the `pack` script instead.

## Environment detection strategy

The environment doctor persists configuration to `cwt_lab/config.json` and walks a progressive detection
strategy:

1. Probe the project-local virtual environment (`.venv/bin/python` on Unix, `.venv/Scripts/python.exe` on
   Windows).
2. Fall back to `python3`/`python` on Unix or `python`/`py -3` on Windows.
3. For each interpreter, attempt to import the high-level `cwt` module. If that fails, attempt to import the
   `experiments` package from `cwt-sim`. As a final fallback, prepend `cwt-sim` to `PYTHONPATH` and retry.
4. The first interpreter that satisfies one of the probes is recorded as the active environment; the
   associated metadata is persisted alongside the configured strategy.

If no interpreter succeeds, the diagnostics panel surfaces the collected error traces. Operators can use the
“Set Python Path” control to manually point to a known-good interpreter.

## Per-run timeouts and diagnostics

Every run launched through the IPC bridge can specify an optional timeout (in milliseconds). When a process
exceeds its budget the run manager terminates the entire process tree, marks the run as `failed`, and stamps
`"error": "timeout"` inside the per-run `diagnostics.json` file. The diagnostics payload captures the
command, arguments, working directory, timestamps in UTC, the computed `PYTHONPATH`, and the environment
snapshot.

The Run Board in the renderer exposes a **Collect diagnostics** button next to each run. Invoking the action
zips the stdout log, diagnostics payload, and environment metadata into `diagnostics-<timestamp>.zip` inside
that run’s artifact directory. The button disables while the archive is being created and surfaces any IPC
errors inline.

## Adding new experiments or commands

1. Implement the experiment inside `cwt-sim` and expose a CLI entrypoint (e.g. `cwt_sim.pipeline.phaseX`).
2. Update the Electron command catalogue in `cwt_lab/electron/runner/commands.ts` with a builder that maps
   your new experiment to the appropriate Python invocation.
3. Extend the renderer with UI controls that call the new IPC endpoint. Prefer wiring through the existing
   `window.CWT.<phase>` namespaces for consistency.
4. Add validator coverage in `cwt_lab/shared/validators.ts` when introducing new numeric ranges or axis
   whitelists.
5. Register unit and integration tests via `vitest` under `cwt_lab/electron` or `cwt_lab/renderer` as
   appropriate. The continuous test suite runs through `npm test` at the repo root, so include your tests
   there to guard against regressions.

With those steps complete, your experiment can be launched from the Run Board or the relevant phase panel,
complete with diagnostics collection, timeout handling, and registry integration.
