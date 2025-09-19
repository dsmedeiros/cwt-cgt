# Continuous Wavelet Transport & Geometric Tensor Toolkit

A research sandbox for exploring **Continuous Wavelet Transport (CWT)** dynamics and the associated **CWT Geometric Tensor (CGT)**. The repository combines theory notes with a Python package (`cwt-sim`) that orchestrates placeholder simulations, parameter sweeps, and evaluation utilities.

## Table of contents
1. [Project overview](#project-overview)
2. [Repository layout](#repository-layout)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Command-line interfaces](#command-line-interfaces)
   * [Run a single loop](#run-a-single-loop-scriptsrun_looppy)
   * [Sweep a parameter grid](#sweep-a-parameter-grid-scriptssweep_gridpy)
   * [Summarise saved runs](#summarise-saved-runs-scriptseval_reportpy)
7. [Non-trivial loops](#non-trivial-loops)
8. [Outputs and run records](#outputs-and-run-records)
9. [Testing and quality](#testing-and-quality)
10. [Further resources](#further-resources)
11. [License and citation](#license-and-citation)

## Project overview
Continuous Wavelet Transport treats macroscopic dynamics as emerging from local propagation on a graph substrate with density-dependent delays. Three interacting layers – probabilistic mass flow (`Q`), phase (`Θ`), and classical readout (`C`) – evolve under a geometry imposed on the control-parameter manifold. That geometry is captured by the CWT Geometric Tensor whose real part behaves as a sensitivity metric and whose imaginary part induces Berry-like curvature effects. The high-level theory is documented in [`theory.md`](theory.md), while this repository provides executable scaffolding for experiments and regression tests.

The Python package housed in `cwt-sim/` wires together:
- graph substrates and transport kernels,
- layered state update rules,
- geometric probes that estimate metric tiles and curvature plaquettes,
- a `RunRecord` data model for recording every intermediate state, and
- Typer-backed command-line interfaces for running loops, sweeping parameter grids, and generating evaluation reports.

Although the shipped implementations fabricate placeholder data, they mirror the interfaces, configuration, and persistence logic of the full simulator. This makes the toolkit suitable for testing downstream analysis pipelines and for iterating on orchestration code before integrating production-grade dynamics.

## Repository layout
- `cwt-sim/` – installable Python package with the simulation orchestrator, CLI entry points, example configurations, and tests.
  - `cwt/` – core modules (geometry, graph, layers, orchestrator, metrics, noise, and IO helpers).
  - `scripts/` – Typer applications providing the documented CLI entry points.
  - `configs/` – ready-made YAML configurations used by the tooling.
  - `tests/` – unit and regression tests that exercise the placeholder implementations.
  - `README.md`, `CITATION.cff`, and `LICENSE` – package-level documentation and metadata.
- `theory.md` – detailed background on CWT/CGT motivation and mathematical formulation.
- `requirements.txt` & `requirements.test.txt` – runtime and testing dependency sets.

## Prerequisites
- **Python**: 3.11 or newer (the package targets Python 3.12 in CI).
- **Operating system**: Linux, macOS, or Windows. The toolkit is CPU-only.
- **Optional**: SciPy (enables sparse-matrix utilities used by some metrics). The core CLI workflows run without it.
- **NetworkX**: 3.1 or newer. Several helpers rely on 3.x-only features (for example the ``alpha`` argument on
  ``random_regular_digraph`` and updated centrality routines), so attempting to run on a 2.x release can yield
  confusing metric outputs. Installing via ``requirements.txt`` ensures a compatible version.

## Installation
1. Clone the repository and create an isolated environment.
   ```bash
   git clone https://github.com/<org>/cwt-cgt.git
   cd cwt-cgt
   python -m venv .venv
   source .venv/bin/activate  # PowerShell: .venv\Scripts\Activate.ps1
   ```
2. Install runtime dependencies for experimentation.
   ```bash
   pip install -r requirements.txt
   ```
3. Install the lighter testing bundle when iterating on the codebase or running CI-equivalent checks.
   ```bash
   pip install -r requirements.test.txt
   ```
4. (Optional) Install the package in editable mode to expose the `cwt` namespace and scripts to your interpreter.
   ```bash
   cd cwt-sim
   pip install -e .
   cd ..
   ```

> **Tip:** The Typer CLIs assume that the `cwt-sim/` directory is on `PYTHONPATH`. Activating the editable install as shown above or invoking the commands via `python -m` from within `cwt-sim/` satisfies this requirement.

## Configuration
Simulation runs are driven by YAML configuration files that map directly onto the [`AppConfig`](cwt-sim/cwt/io/config.py) Pydantic model. The top-level keys mirror the dataclasses used by the orchestration layer:

| Section | Purpose | Notable fields |
| ------- | ------- | -------------- |
| `graph` | Graph substrate used to build transport kernels. | `kind`, `weights`, `delays` |
| `params` | Parameter sweep definition and step count. | `knobs`, `rho_center`, `tau_center`, `zeta_phase_center`, `steps` |
| `geometry` | Settings for metric tiles and curvature sampling. | `delta_frac`, `compute_metric`, `compute_curvature`, `adapt_levels` |
| `dynamics` | Layer coupling coefficients. | `eta_q`, `zeta`, `omega_scale` |
| `geometric_coupling` | Controls curvature-to-bias conversion. | `alpha`, `beta`, `xi_kind`, `corner_area_mode` |
| `readout` | Readout scheduling and metadata. | `type`, `T`, `memory_form`, `params` |
| `noise` | Gaussian perturbations applied during updates. | `phase_std`, `amp_noise`, `delay_std` |
| `seed` / `out_dir` | Random seed for reproducibility and destination for saved runs. | – |

Starter files are available under `cwt-sim/configs/`:
- `default.yaml` – dense configuration with metric and curvature estimation enabled.
- `grid_scan.yaml` – tuned for scripted grid sweeps with a custom output directory.
- `small_ring.yaml`, `stage0_dimer.yaml` – additional templates for experiments.
- `loop_tau_zeta.yaml`, `loop_tau_zeta_phase.yaml` – ready-made hetero-ring loops over Θ-coupling magnitude and phase.

Quickly tailor a loop by listing the axes in `params.knobs` and supplying per-knob centres and extents:

```yaml
params:
  knobs: [tau, zeta_phase]
  tau:
    center: 0.80
    extent: 0.02
  zeta_phase:
    center: 0.00
    extent: 0.02
```

`ParamsConfig` accepts matching `*_center`/`*_extent` pairs (for example `zeta_phase_center` and `zeta_phase_extent`) so scripted tooling can synthesise loops without verbose nested mappings.

Use the `--dry-run` switch on the CLI to validate configurations without writing to disk. Typer will emit a prettified JSON representation of the resolved configuration, making it easy to spot mistakes.

## Command-line interfaces
All CLIs live in `cwt-sim/scripts/` and expose a Typer-powered `--help` page. You can invoke them either via `python -m scripts.<name>` from the `cwt-sim/` directory or through the entry points installed by `pip install -e .`.

### Run a single loop (`scripts/run_loop.py`)
Validate a configuration and run a short simulation, persisting the resulting run bundle under the configured `out_dir` (default `runs/`).

```bash
cd cwt-sim
python -m scripts.run_loop --config configs/default.yaml
```

**Key options**
- `--config, -c PATH` (required): YAML configuration file.
- `--out PATH`: Override the `out_dir` defined in the config.
- `--seed INTEGER`: Override the configuration’s random seed.
- `--dry-run`: Print the resolved configuration and exit without writing outputs.
- `--simulate/--fabricate`: Toggle between executing the real loop (default) and emitting a lightweight placeholder record.

**Outputs**
- With `--dry-run`, the command prints the final configuration as JSON and exits with status 0.
- Without `--dry-run`, the CLI executes the loop (or fabricates a placeholder when `--fabricate` is supplied), persists the resulting [`RunRecord`](cwt-sim/cwt/orchestrator/scheduler.py) via [`save_run`](cwt-sim/cwt/io/registry.py), and prints a one-line JSON payload such as:
  ```json
  {"run_id": "6bb7c7f2f53c46a3a4b7b0f4f3444b12", "out_dir": "runs/6bb7c7f2f53c46a3a4b7b0f4f3444b12"}
  ```
  Each run directory contains `meta.json` plus any NumPy arrays referenced by the record; downstream tooling (`eval_report`, notebooks, etc.) consumes these artefacts directly.

### Sweep a parameter grid (`scripts/sweep_grid.py`)
Generate multiple placeholder runs that traverse a grid defined by the configuration’s `params` section.

```bash
cd cwt-sim
python -m scripts.sweep_grid --config configs/grid_scan.yaml --limit 5
```

**Key options**
- `--config, -c PATH` (required): YAML configuration file.
- `--out PATH`: Override the output directory.
- `--limit INTEGER`: Restrict the number of generated runs (defaults to the configured `steps`).

**Outputs**
- A JSON object containing the UUIDs of the fabricated runs and the count of generated directories.
  ```json
 {"runs": ["7a...", "28...", "c1..."], "count": 3}
  ```

### Summarise saved runs (`scripts/eval_report.py`)
Aggregate persisted runs into a compact report that tracks geometric metrics and curvature-driven bias.

## IPC API (channels & payloads)
In addition to the Typer CLIs, the toolkit exposes a lightweight inter-process control (IPC) facade that mirrors the workflow
stages implemented by the orchestration scripts. Every method returns an envelope of the form
`{ ok: boolean, data?: T, error?: string }`, enabling callers to short-circuit on transport failures while leaving the payload
schema unchanged.

### Environment helpers
| Method | Description |
| ------ | ----------- |
| `env.detect()` | Probes the active environment, preferring virtual environments, and verifies that the `cwt` package can be imported via `python -c "import cwt"`. |
| `env.setPythonPath(path: string)` | Overrides the Python interpreter path used when spawning subprocesses. |
| `env.getConfig()` | Reports the resolved repository root, working directories, and artifact destination paths. |

### Generic run orchestration
| Method | Description |
| ------ | ----------- |
| `run.create({ experiment, args, workdir })` | Launches a background simulation or fabrication run (mirroring the CLIs) and returns a `runId`. |
| `run.abort({ runId })` | Requests early termination of a live run. |
| `run.tail({ runId, fromByte? })` | Streams incremental stdout/stderr output from a run, optionally resuming from a byte offset. |
| `run.openArtifacts({ runId })` | Lists generated artifact paths for the completed run. |

### Phase-specific workflows
The remaining channels map to the numbered research phases and their Python entry points. All commands accept structured JSON
arguments mirroring the CLI flags used in the corresponding script.

| Phase | Method | Purpose |
| ----- | ------ | ------- |
| Phase 1 | `phase1.map({ axes, ranges, gridSize, graphs, bootstrap, topK, seed, outDir })` | Executes `gateB_ridge_finder/run.py` to scan ridge structures across the specified axis grid. |
| Phase 2 | `phase2.correlate({ metricsDirs, thresholdMode, thresholdValue\|percentile })` | Parses saved CSV/JSON metrics to compute correlation tables and AUCs without invoking Python workers. |
| Phase 3 | `phase3.loopAtHotspot({ hotspotsJson, axes, extents, fsGuard, graph, limit, seed })` | Kicks off hotspot-focused loops to refine free-surface estimates. |
| Phase 3 | `phase3.guidedLoop({ center, graph, axes3, amplitudes, fsGuard, stepsList, minPhi, settle, handleSteps })` | Orchestrates sequential `wilson_loop_3d/run.py` executions, returning the collected run records and whether the guard criteria were satisfied. |
| Phase 4 | `phase4.wilson3d({ axes3, center, amplitudes, steps, settle, fsGuard, graph, seed, outDir })` | Runs the full 3D Wilson loop explorer with configurable grids and guards. |
| Phase 4 | `phase4.torusPlateau({ axes, gridSize, disorderList, centersExtents, outDir })` | Generates torus plateau scans across disorder settings. |
| Phase 5 | `phase5.graphFamily({ families, axes, gridSize, extents, seed, outDir })` | Sweeps over graph families to catalogue phase responses. |
| Phase 5 | `phase5.inverseDesign({ axes, center, extentPair, budgetSteps, maxFs, targetIndex, outDir })` | Launches the inverse-design loop to seek configurations matching the requested target. |
| Phase 5 | `phase5.noiseRobust({ phaseStd, ampStd, delayStd, numTrials, loopSteps, axes, outDir })` | Evaluates the robustness of loops under stochastic perturbations. |
| Phase 5 | `phase5.betaSweep({ configPath, betas[] })` | Generates patched YAML configs and sequentially runs `scripts/run_loop.py`, reporting the run IDs for each β value. |

### Artifacts, registry, and recipes
| Method | Description |
| ------ | ----------- |
| `artifacts.list({ under })` | Returns a tree view of artifacts suitable for browsing UIs. |
| `registry.query({ phase?, experiment?, limit? })` | Lists recent runs with their metrics, completion status, and metadata tags. |
| `recipes.save({ name, params, command, seed, envInfo })` | Persists a reusable recipe template that records inputs and environment details. |
| `recipes.list()` | Enumerates saved recipes. |
| `recipes.run({ id })` | Executes a previously saved recipe. |

> **Status:** The IPC facade now delegates each channel to the corresponding Python module (or Node analysis in the case of the
> Phase 2 correlation helper), streams output via the run manager, updates the registry database, and returns structured payloads
> for higher-level orchestrations such as guided Wilson loops and β sweeps.

```bash
cd cwt-sim
python -m scripts.eval_report runs --format markdown --report reports/summary.md
```

**Key options**
- `runs` (argument): Directory containing one or more run folders with `meta.json` files.
- `--format, -f {json,markdown}`: Select JSON (default) or Markdown output.
- `--report, -r PATH`: When using Markdown, write the table to a file in addition to printing it.

**Outputs**
- JSON mode emits structured data with per-run summaries and a `sign_flip_ok` indicator derived from orientation checks.
  ```json
  {
    "count": 2,
    "sign_flip_ok": true,
    "runs": [
      {
        "run_id": "...",
        "label": "default_0",
        "orientation": "CW",
        "phi_flux": -1.2e-03,
        "R_bias": 4.5e-04,
        "fs_stats": {"mean": 2.8e-02, "kappa1": 1.5e-02, ...},
        "sign_flip": true
      }
    ]
  }
  ```
- Markdown mode prints a table with loop orientation, flux, bias, and curvature statistics. When both clockwise and counter-clockwise loops are present, the footer reports whether the curvature sign flips as expected.

### Stage-0 analytic validation (`experiments/stage0_analytic/run.py`)
Run the closed-form sanity checks for the CGT estimators. The command generates JSON summaries, tabular outputs, and optional figures.

```bash
cd cwt-sim
python -m experiments.stage0_analytic.run --output-dir experiments/stage0_analytic/output
```

**Key options**
- `--output-dir PATH`: Directory that receives the JSON summary, tables, and figures.
- `--format {parquet,csv}`: Storage format for the tabular data. Parquet is used when `pyarrow` is available; otherwise the script automatically falls back to CSV.
- `--no-figures`: Skip plotting when running in headless environments.

**Outputs**
- `records.json` consolidates the analytic metrics.
- The `tables/` subdirectory contains either Parquet or CSV files depending on the selected format and `pyarrow` availability.
- `figures/` includes the validation plots unless `--no-figures` is provided.

The ring plaquette examples in this stage lean on a deliberately asymmetric
three-node substrate. Unequal propagation delays inject the τ-gradient needed
to excite Berry-like curvature when the Θ-coupling is looped. You can build the
same substrate programmatically via the dedicated factory:

```python
from cwt.graph.factories import ring3_hetero

substrate = ring3_hetero()
```

The default delays ``[1.0, 1.5, 2.2]`` align with the hetero-ring templates in
`cwt-sim/configs/` and with the Stage-0 analytics.

## Non-trivial loops

Two hetero-ring templates in `cwt-sim/configs/` showcase Θ-coupling effects that go beyond trivial rectangular sweeps:

- **(τ, ζ)** – `loop_tau_zeta.yaml` keeps the Θ-coupling phase locked while varying its magnitude. Running
  ```bash
  cd cwt-sim
  python -m scripts.run_loop --config configs/loop_tau_zeta.yaml
  ```
  yields a non-zero Berry-like `phi_flux` despite the flux being small compared with the raw loop area, and flipping the loop orientation inverts the reported curvature sign.
- **(τ, ζ_phase)** – `loop_tau_zeta_phase.yaml` treats the Θ-coupling phase as a primary knob. Execute
  ```bash
  cd cwt-sim
  python -m scripts.run_loop --config configs/loop_tau_zeta_phase.yaml
  ```
  to induce controlled Θ-frustration: the fabricated run records a `phi_flux` magnitude that stays well below the geometric area while the orientation flag `R` changes sign between clockwise and counter-clockwise traversals.

Both recipes use uniform-charge, one-hot readouts so the curvature signatures remain easy to inspect directly in the saved `meta.json` payloads.

## Outputs and run records
Every CLI workflow produces or consumes a [`RunRecord`](cwt-sim/cwt/orchestrator/scheduler.py) – a dataclass capturing time-series trajectories (`pQ_traj`, `theta_traj`, `psi_traj`), geometric tiles (`g_tiles`, `omega_tiles`), curvature-derived biases, and readout snapshots. The `save_run` helper serialises these structures to disk by writing `meta.json` alongside any NumPy arrays required for reconstruction. The `eval_report` command deserialises the bundles, computes [`LoopSummary`](cwt-sim/cwt/metrics/eval_curves.py) metrics (flux, curvature bias, orientation, minimum overlaps, Fubini–Study statistics), and enforces optional sign-flip checks between clockwise and counter-clockwise runs.

## Testing and quality
- Run the curated unit and regression suites with:
  ```bash
  pytest cwt-sim/tests
  ```
- Formatting is enforced with **Black** (line length 110) and imports are checked via **Ruff**. Apply them manually when preparing contributions:
  ```bash
  black cwt-sim
  ruff check cwt-sim
  ```
- Type hints are validated for select geometry modules with **mypy**:
  ```bash
  mypy --config-file cwt-sim/pyproject.toml
  ```

## Further resources
- [`theory.md`](theory.md) – conceptual overview of the CWT/CGT framework.
- `cwt-sim/notebooks/` – exploratory notebooks illustrating geometry calculations.
- `cwt-sim/experiments/` – scripts for reproducing packaged experiments.

## License and citation
The simulation scaffolding ships with a placeholder [license](cwt-sim/LICENSE) and [CITATION.cff](cwt-sim/CITATION.cff). Update these files with project-specific metadata before public release or academic dissemination.
