# Causal Web Theory & Geometric Tensor Toolkit

A multi-language research sandbox for studying **Causal Web Theory (CWT)** and the associated **CWT Geometric Tensor (CGT)**. The repository couples a Python simulation package with an Electron + React desktop laboratory so that analytic experiments, automated sweeps, and operator-facing tooling can share the same configuration and persistence model.

## Table of contents
1. [Project overview](#project-overview)
2. [Repository structure](#repository-structure)
3. [Python simulation toolkit](#python-simulation-toolkit)
   * [Environment setup](#environment-setup)
   * [Command-line workflows](#command-line-workflows)
   * [Configuration files](#configuration-files)
   * [Experiments and notebooks](#experiments-and-notebooks)
4. [Electron + React laboratory](#electron--react-laboratory)
   * [Node environment](#node-environment)
   * [Desktop shell commands](#desktop-shell-commands)
   * [Run manager & IPC bridge](#run-manager--ipc-bridge)
5. [Run artifacts and registry](#run-artifacts-and-registry)
6. [Testing and quality](#testing-and-quality)
7. [Additional documentation](#additional-documentation)
8. [License and citation](#license-and-citation)

## Project overview
Causal Web Theory treats macroscopic dynamics as emerging from local propagation on weighted, delay-aware substrates. Three coupled layers — probabilistic mass flow (`Q`), relative phase (`Θ`), and classical readout (`C`) — evolve under a geometry captured by the CWT Geometric Tensor. The codebase provides:

- **`cwt-sim/`** – a Python package with placeholder-yet-structured simulators, Typer-based CLIs, and a rich library of experiments that mirror the production orchestration stack.
- **`cwt_lab/`** – an Electron + React desktop application that fronts the simulation stack with phase-specific dashboards, run management, diagnostics, and recipe automation.
- **`electron/runner/`** – a TypeScript command builder and parser suite that backs the IPC bridge used by the desktop shell and exposes Jest-tested helpers for spawning Python processes from Node.
- Supporting documentation (`theory.md`, `USER_GUIDE.md`) plus curated configuration templates, notebooks, and regression tests.

Even though many routines fabricate data, they respect the same schema, dependency graph, and persistence contracts expected by downstream analytics. This allows developers to iterate on orchestration logic, UI flows, and integration tests before committing to full-fidelity physics.

## Repository structure
- `cwt-sim/` – installable Python package.
  - `cwt/` – geometry, graph factories, IO helpers, orchestrators, metrics, and noise models.
  - `scripts/` – Typer entry points (`run_loop`, `sweep_grid`, `eval_report`, `demo_operator_view`).
  - `configs/` – YAML templates referenced by CLIs and experiments.
  - `experiments/` – runnable research workflows (stage-0 analytics, Wilson loops, torus plateau scans, inverse design, and more).
  - `tests/` – unit/regression suites configured through `pyproject.toml`.
- `cwt_lab/` – Electron workspace.
  - `electron/` – main process, preload script, IPC handlers, registry, and diagnostics collectors.
  - `renderer/` – React application with per-phase dashboards, run board, and environment doctor.
  - `shared/` – schema validators, constants, and test utilities shared between processes.
- `electron/runner/` – standalone command builders + Jest coverage for Node-side automation.
- `docs/` – UI screenshots embedded in the user guide.
- `USER_GUIDE.md` – operator-facing walkthrough of the desktop shell.
- `theory.md` – mathematical background for CWT/CGT derivations.

## Python simulation toolkit

### Environment setup
1. Provision Python 3.11+ and create a virtual environment under the repository root.
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # PowerShell: .venv\Scripts\Activate.ps1
   ```
2. Install runtime dependencies for interactive work.
   ```bash
   pip install -r requirements.txt
   ```
3. Install the development and test extras when running the suite or static analysis.
   ```bash
   pip install -r requirements.test.txt
   ```
4. (Optional) Install the package in editable mode to expose the `cwt` namespace and scripts to the active interpreter.
   ```bash
   pip install -e cwt-sim
   ```

### Command-line workflows
All entry points live in `cwt-sim/scripts/` and can be invoked with `python -m scripts.<name>` once the editable install (or an explicit `PYTHONPATH`) is active.

#### Run a single loop – `scripts/run_loop.py`
Validate a YAML configuration, then either execute a short simulation or fabricate a placeholder bundle.
```bash
cd cwt-sim
python -m scripts.run_loop --config configs/default.yaml
```
Key switches:
- `--out PATH` – override the output directory recorded in the config.
- `--seed INTEGER` – override the random seed prior to execution.
- `--dry-run` – print the resolved configuration as JSON and exit without generating artifacts.
- `--simulate/--fabricate` – toggle between running the scheduler and emitting a lightweight placeholder via `fabricate_record`.

#### Sweep a parameter grid – `scripts/sweep_grid.py`
Generate multiple placeholder runs that walk the configuration’s parameter grid.
```bash
cd cwt-sim
python -m scripts.sweep_grid --config configs/grid_scan.yaml --limit 5
```
The command fabricates `limit` (or `params.steps`) runs, persists them via `save_run`, and prints the generated UUIDs.

#### Summarise saved runs – `scripts/eval_report.py`
Aggregate previously saved runs into JSON or Markdown reports that expose curvature bias, loop orientation, sign-flip checks, and Fubini–Study statistics.
```bash
cd cwt-sim
python -m scripts.eval_report runs --format markdown --report reports/summary.md
```
Use `--format json` for machine consumption or `--report PATH` to persist Markdown alongside stdout.

#### Operator-view demo – `scripts/demo_operator_view.py`
Integrate the QP-1 example’s curvature density to validate the operator-bundle helpers.
```bash
cd cwt-sim
python -m scripts.demo_operator_view --samples 4096
```
The script prints the integrated Ω density and its deviation from the expected `2π` reference.

### Configuration files
Simulation runs are parameterised through YAML files that map directly onto the [`AppConfig`](cwt-sim/cwt/io/config.py) Pydantic model. Key sections include:

| Section | Purpose | Representative fields |
| ------- | ------- | --------------------- |
| `graph` | Selects graph factories and delay/weight settings for the substrate. | `kind`, `weights`, `delays` |
| `params` | Defines sweep knobs, centres, extents, and step counts consumed by the parameter path builder. | `knobs`, `steps`, `<knob>_center`, `<knob>_extent`, `model_extra` |
| `geometry` | Controls metric/curvature sampling and adaptive neighbourhood behaviour. | `sample_mode`, `delta_frac`, `compute_metric`, `compute_curvature`, `adapt_levels` |
| `dynamics` | Configures layer couplings. | `eta_q`, `zeta`, `omega_scale` |
| `geometric_coupling` | Converts curvature tiles into readout bias. | `alpha`, `beta`, `xi_kind`, `corner_area_mode` |
| `readout` | Records snapshot cadence and metadata for classical observables. | `type`, `T`, `memory_form`, `params` |
| `noise` | Injects stochastic perturbations. | `phase_std`, `amp_noise`, `delay_std` |
| `seed`, `out_dir` | Reproducibility and artifact destination. | – |

Starter configurations under `cwt-sim/configs/` include dense defaults, grid sweeps, hetero-ring loop recipes, and stage-0 templates that align with the analytic experiments. Use `--dry-run` to validate edits before launching long jobs.

### Experiments and notebooks
The `experiments/` namespace mirrors the production calibration phases. Representative entry points:

- `experiments.stage0_analytic.run` – closed-form sanity checks for CGT estimators (figures + tabular exports).
- `experiments.wilson_loop_3d.run` – Wilson-loop explorer with handle guards, hot-start logic, and curvature telemetry.
- `experiments.torus_plateau.run` – torus plateau sweeps across disorder settings and axis pairs.
- `experiments.inverse_design.run` & `experiments.graph_family.run` – optimisation and comparative studies across graph ensembles.
- `experiments.xi_dynamic_demo.run` – showcases time-dependent curvature coupling.

Launch them with `python -m experiments.<module>.run ...` after activating the environment. Exploratory notebooks live in `cwt-sim/notebooks/` for quick visualisation of geometry kernels and metric tiles.

## Electron + React laboratory

### Node environment
The desktop shell relies on Node.js (18+ recommended) and npm. Install dependencies from the repository root:
```bash
npm install
npm --prefix cwt_lab install
```
The post-install hook wires Electron Builder’s native dependencies, while the root workspace exposes shared Jest tooling for the standalone command builders.

### Desktop shell commands
Start a hot-reloading development session:
```bash
npm --prefix cwt_lab run dev
```
Electron-Vite launches the renderer on port `5173` and attaches the Electron host to the compiled entry points. Additional scripts:
- `npm --prefix cwt_lab run build` – bundle renderer + preload assets without packaging.
- `npm --prefix cwt_lab run dist` – create distributable artifacts via Electron Builder.
- `npm --prefix cwt_lab run pack` – generate unpacked directories for manual inspection.

### Run manager & IPC bridge
The preload script exposes a `window.CWT` API that fronts the underlying IPC bridge. Command builders defined in `cwt_lab/electron/runner/` and `electron/runner/` map UI interactions onto Python invocations (`experiments.*`, Typer CLIs, and registry helpers). Key capabilities:

- Environment detection that prioritises the repo-local virtual environment, falls back through system interpreters, and records the chosen interpreter plus probe results in `cwt_lab/config.json`.
- Run orchestration with streaming stdout capture, timeouts, artifact enumeration, and diagnostics zipping.
- Phase-specific helpers for ridge mapping, guided Wilson loops, torus plateau scans, graph family sweeps, and optimisation recipes.
- Recipe management (save/list/run/export) and preview builders so operators can vet the CLI payload before launching long jobs.

Consult `USER_GUIDE.md` for screenshots and a phase-by-phase walkthrough of the laboratory UI.

## Run artifacts and registry
Every workflow ultimately persists a [`RunRecord`](cwt-sim/cwt/orchestrator/scheduler.py) containing trajectories (`pQ_traj`, `theta_traj`, `psi_traj`), geometric tiles, curvature-derived bias, and readout snapshots. `save_run` writes `meta.json` plus referenced NumPy arrays, enabling downstream consumers (CLI reporters, experiments, and the Electron registry) to reload runs without recomputing dynamics. The `scripts.eval_report` CLI and the desktop Run Board both reuse this schema to display orientation, Φ flux, Fubini–Study statistics, and sign-flip checks.

## Testing and quality
- **Python**
  - `pytest cwt-sim/tests`
  - `ruff check .`
  - `black --check cwt-sim`
  - `mypy --config-file cwt-sim/pyproject.toml`
- **Node / Electron**
  - `npm test` – runs the Jest suite under `electron/runner` and delegates to `cwt_lab`’s Vitest suite.
  - `npm --prefix cwt_lab run lint`
  - `npm --prefix cwt_lab run typecheck`
  - `npm --prefix cwt_lab test`

Install `requirements.test.txt` and `npm install` dependencies beforehand so the checks can import the package and compile TypeScript sources.

## Additional documentation
- [`theory.md`](theory.md) – mathematical motivation and derivations for CWT/CGT constructs.
- [`USER_GUIDE.md`](USER_GUIDE.md) – operator-facing walkthrough of the Electron laboratory.
- `cwt_lab/README.md` – engineering guide for extending the desktop shell and IPC catalog.
- `cwt-sim/README.md` – package-level reference covering modules, metrics, and developer tips.

## License and citation
The simulation scaffolding ships with placeholder metadata in [`cwt-sim/LICENSE`](cwt-sim/LICENSE) and [`cwt-sim/CITATION.cff`](cwt-sim/CITATION.cff). Update these files with project-specific details before public release or academic dissemination.
