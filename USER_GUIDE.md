# CWT Lab – User Guide

Welcome to the Curvature Workflow Toolkit (CWT) Lab. This guide walks through each phase of the calibration
journey, explains the telemetry terms that appear across the UI, and documents the built-in troubleshooting
playbook.

## Reading the metrics at a glance

- **FS (Fubini–Study) distance**: measures how far the quantum state jumps between loop steps. Think of it as
  the stride length of the climb—short strides (low FS) keep the system stable while tall spikes mean the loop
  is stumbling.
- **Φ (phi)**: reports the curvature of the ridge you are following. Values near zero indicate a flat plateau;
  larger magnitudes signal a steep ridge or valley.
- **R (readout bias)**: tracks the curvature-induced preference of the classical readout. Values near 1 indicate
  a strong bias toward the hotspot orientation; values closer to 0 signal a balanced, ambiguity-prone readout.

These three metrics appear across the Run Board, diagnostics logs, and per-phase dashboards. Keep them in mind
when deciding whether to tighten guards or adjust parameters.

## Layout overview

- **Header controls**: Use the theme toggle to switch between light and dark palettes and the `?` button to open
  the contextual Help Drawer for whichever tab is active. Keyboard shortcuts are surfaced next to the title—`⌥R`
  refreshes the active run action, `⌥A` aborts the current log tail or job, and `⌥T` flips the theme without
  touching the mouse.
- **Demo mode**: The **Demo: On/Off** toggle injects curated runs, artifacts, and recipes so you can explore the
  UI offline. Disable it once a live registry is available to read real metrics.
- **Experiment & substrate selectors**: Tabs that analyse saved data (Phase 2 onward, Torus Plateau, Artifact
  Browser) share the selectors in the header. Choose an experiment to list its substrates, then pick a substrate
  directory to scope the Phase tools. The watchers behind the scenes update the dropdowns automatically when new
  runs land on disk.

## Phase walkthrough

### Run Board – monitor and collect diagnostics

![Run Board overview](docs/screenshots/run-board.svg)

The Run Board groups recent activity by experiment, showing phase badges, last-updated timestamps, and the
artifacts directory so you can triage multi-phase calibrations quickly. Click a row to expand the runs inside,
then use the action buttons to tail logs, collect diagnostics, or remove stale records.

- **Diagnostics bundles**: Use **Collect diagnostics** when support asks for logs—the UI will produce a ZIP that
  includes stdout chunks, `diagnostics.json`, and environment metadata.
- **Log viewer**: **View log** streams stdout/stderr in 64 KB chunks. **Load more** backfills older output,
  **Refresh** fetches the latest bytes, and the footer calls out the byte range currently in view. Press `⌥A`
  to cancel a long-running tail request.
- **Deletion workflow**: Delete individual runs or entire experiments after confirming the prompt. The table will
  refresh automatically, and any open log viewers close to avoid dangling references.
- **Keyboard shortcuts**: Press `⌥R` to refresh the board without leaving the keyboard. Status messages confirm
  which action triggered after each shortcut fires.

### Phase 1 – Mapping

![Phase 1 mapping](docs/screenshots/phase1.svg)

Phase 1 sweeps the Ω landscape to highlight promising regions. Adjust the extent and percentile guards on the
right. Warm tiles indicate steep gradients worth sampling in later phases.

### Phase 2 – Feature scans

![Phase 2 feature scans](docs/screenshots/phase2.svg)

Phase 2 correlates scalar features against the FS threshold you choose. Bars coloured in gold signal strong
positive influence on the guard, and the ROC preview shows how cleanly the classifier separates hot from cold
regions.

### Phase 3 – Guided loops

![Phase 3 guided loops](docs/screenshots/phase3.svg)

Phase 3 loops around hot spots using the axes and amplitudes you select. The trace overlays Φ, FS, and R so you
can tell whether the guard is holding while the ridge curves. Watch for FS spikes mid-loop—they usually mean
one of the axes needs tightening. Successful runs now emit a `phase3_loop_summary.json` next to the evaluated
substrate so later phases can reuse the calibrated centres, extents, and guard decisions without rerunning the
validator.

### Phase 4 – 3D explorer

![Phase 4 explorer](docs/screenshots/phase4.svg)

Phase 4 renders the torus plateau and overlays candidate handles. Compare against a known 2D recipe to see if
the 3D lift uncovers new structure or merely confirms a flat patch. Use the new “Phase 3 import” controls to
select a Phase 1/3 experiment and substrate—the explorer automatically loads the saved Phase 3 summary,
hydrates the centre, amplitudes, guard and settle defaults, and includes the provenance when dispatching the
Wilson-loop CLI.

### Phase 5 – Optimisation

![Phase 5 optimisation](docs/screenshots/phase5.svg)

Phase 5 drives a full optimiser over the ridge. The convergence trace shows FS and overlap improving. Export
results once improvements plateau to avoid drift.

### Torus Plateau – sweep the ridge in 3D

Use the Torus Plateau tab to launch `phase4.torusPlateau` surveys and inspect their summaries. Configure the two
axes, grid density, disorder samples, and τ/ζ centres/extents, then review the command preview before launching.
When a run finishes, the viewer fetches `summary.json`, lists each disorder sample, and renders heatmaps plus
guard coverage statistics so you can spot promising handles.

### Artifact Browser – inspect saved outputs

The Artifact Browser queries the registry (or the demo catalogue) and organises runs by phase. Filter the list by
phase, search by tag or keyword, and select a record to reveal its key metrics. When Plotly-compatible traces are
available the panel renders a preview chart; otherwise it shows the summary text pulled from `summary.json`.

### Recipe comparison – side-by-side decisions

Enable demo mode or save recipes to compare two protocols. The comparison table aligns shared metrics, reports the
percentage deltas, and renders Plotly traces for Φ flux and guard margin so you can judge convergence histories at
a glance.

### Env Doctor – interpreter health

![Environment doctor](docs/screenshots/env-doctor.svg)

The Env Doctor inspects candidate Python interpreters. Green badges mark interpreters that can import `cwt` or
fall back to the module-based strategy. Orange/red cards detail what failed so you can patch dependencies. While
the scan runs the status line at the top of the panel cycles through each diagnostic step so you know the
application is still working. Use **Browse…** next to the Python executable field to pick the interpreter on
disk—handy when pointing the lab at a Windows virtual environment or a freshly-installed interpreter.

## Demo mode cheat sheet

Demo mode seeds the UI with curated, deterministic data so you can rehearse workflows before wiring up the real
registry:

- **Run Board**: populates sample phase runs, log output, and diagnostics bundles.
- **Artifact Browser**: serves a catalogue of cross-phase artifacts with metrics and Plotly previews.
- **Recipe comparison**: includes multiple saved protocols so you can exercise the comparison workflow.

Turn demo mode off once your backend is ready; the live registry APIs take over automatically.

## Troubleshooting

- **FS spikes**: When FS distance suddenly climbs, reduce the loop amplitude or tighten the guard in Phase 3.
  If spikes persist, revisit Phase 1 to map a broader region—the ridge may be kinked or split.
- **Φ ≈ 0 or below the minimum**: A flat or underperforming φ suggests you are on a plateau. Increase the τ/ζ
  amplitudes in Phase 3, relax the Φ threshold slightly, widen the extent in Phase 1, or switch axes to tilt the
  loop towards a direction with more curvature.
- **Import errors in Env Doctor**: Use the **Set Python Path** option to point to the virtual environment you
  prepared with `pip install -r requirements.txt` and `pip install -r requirements.test.txt`. The diagnostics
  panel will show the exact import failure to guide additional installs.

## Collecting diagnostics for support

1. Open the Run Board and locate the run in question.
2. Click **Collect diagnostics**. The button will disable while the archive is created.
3. When the notice displays the ZIP path, open the artifacts directory on disk and share the file with support.

The archive includes the stdout/stderr capture, the structured `diagnostics.json` with timestamps in UTC, and a
snapshot of the detected Python environment.
