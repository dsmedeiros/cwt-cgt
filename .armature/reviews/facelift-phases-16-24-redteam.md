# Red Team Review: facelift-phases-16-24

## Summary

All nine phase analysis modules (16-24) pass Python import resolution cleanly. The `from ..X import Y` rewrites are syntactically correct and every imported symbol exists in the target module. However, I found three categories of issues: (1) hardcoded path strings that reference directories which do not exist in the current repo layout, producing silent file-write misdirection at runtime; (2) an inconsistent path convention in phase 17 that doubles a path component; and (3) fragile transitive import chains that will break silently if upstream modules change their own imports. The path issues are the most operationally significant -- they will cause report and summary JSON files to be written to wrong (auto-created) directories, or cause FileNotFoundError when reading source artifacts.

## Critical Findings

### CRITICAL-1: Phases 22, 23, 24 use `03_benchmarks` which does not exist

- **Files and lines:**
  - `phase22_analysis.py` line 135: `results_root = project_root / '03_benchmarks' / 'results'`
  - `phase23_analysis.py` line 77: `results_root = project_root / '03_benchmarks' / 'results'`
  - `phase24_analysis.py` line 218: `results_root = project_root / '03_benchmarks' / 'results'`
- **What the bug is:** These modules construct a results path using `03_benchmarks`, a directory name from the pre-migration flat package layout (`cwt_cgt/`). The actual directory in the current repo is `cgt_benchmarks`. There is no `03_benchmarks` directory anywhere in the repository.
- **How to trigger it:** Call `phase22_payload(project_root=Path('cwt-sim'))`, `phase23_payload(project_root=Path('cwt-sim'))`, or `phase24_payload(project_root=Path('cwt-sim'))`. The functions will raise `FileNotFoundError` when trying to read source artifacts from the nonexistent path.
- **What happens when triggered:** Phase 22 raises `FileNotFoundError` at line 139 (`source_path.exists()` returns False). Phase 23 raises at line 82. Phase 24 will silently fail to find the zero-crossing file (`_load_zero_crossing` returns `None`) and then proceed to write results to `cwt-sim/03_benchmarks/results/benchmark_C_ring/` after `mkdir(parents=True)` creates it, fragmenting output across two directory trees.
- **Severity:** CRITICAL -- these phases cannot execute against the current repo layout without error or silent output misdirection.

### CRITICAL-2: Phases 22, 23, 24 write reports/plots to `05_reports` which does not exist

- **Files and lines:**
  - `phase22_analysis.py` line 223: `plots_dir = project_root / '05_reports' / 'plots' / ...`
  - `phase22_analysis.py` line 235: `summary_path = project_root / '05_reports' / 'phase22_summary.json'`
  - `phase23_analysis.py` line 210: `plots_dir = project_root / '05_reports' / 'plots' / ...`
  - `phase23_analysis.py` line 219: `summary_path = project_root / '05_reports' / 'phase23_summary.json'`
  - `phase24_analysis.py` line 351: `plots_dir = project_root / '05_reports' / 'plots' / ...`
  - `phase24_analysis.py` line 358: `summary_path = project_root / '05_reports' / 'phase24_summary.json'`
- **What the bug is:** Reports and plot files are written to `cwt-sim/05_reports/` via `mkdir(parents=True)`. The correct location is `cwt-sim/cgt_benchmarks/reports/`. Output will silently land in the wrong directory, invisible to downstream consumers expecting `cgt_benchmarks/reports/`.
- **Severity:** CRITICAL -- silently produces output in a wrong directory tree.

### HIGH-1: Phase 17 `phase17_payload` doubles the `cgt_benchmarks` path component

- **File and lines:**
  - `phase17_analysis.py` line 374: `reports_dir = output_root / 'cgt_benchmarks' / 'reports'`
  - `phase17_analysis.py` line 381: `reports_dir = output_root / 'cgt_benchmarks' / 'reports'`
- **What the bug is:** When `output_root` is `cwt-sim/cgt_benchmarks/results` (as set by the run script), this produces `cwt-sim/cgt_benchmarks/results/cgt_benchmarks/reports`. The correct path would be `output_root.parent / 'reports'` = `cwt-sim/cgt_benchmarks/reports`.
- **How to trigger it:** Call `phase17_payload(output_root=Path('cwt-sim/cgt_benchmarks/results'))` or run `scripts/cgt/run_phase17_analysis.py`.
- **What happens when triggered:** Summary JSON and report markdown are written to a nested `results/cgt_benchmarks/reports/` directory instead of the sibling `cgt_benchmarks/reports/` directory. The `mkdir(parents=True)` call silently creates the wrong path.
- **Severity:** HIGH -- silent output misdirection for phase 17 report artifacts only.

### HIGH-2: Phases 16, 18, 19, 20, 21 write reports to `cwt-sim/05_reports` instead of `cwt-sim/cgt_benchmarks/reports`

- **Files and lines:**
  - `phase16_analysis.py` line 382: `reports_dir = output_root.parents[1] / '05_reports'`
  - `phase16_analysis.py` line 389-390: `project_root = output_root.parents[1]` then `reports_dir = project_root / '05_reports'`
  - `phase18_analysis.py` line 336: `report_dir = output_root.parents[1] / '05_reports'`
  - `phase19_analysis.py` line 375: `reports_dir = output_root.parents[1] / '05_reports'`
  - `phase20_analysis.py` line 442: `reports_dir = output_root.parents[1] / '05_reports'`
  - `phase21_analysis.py` line 290: `reports_dir = output_root.parents[1] / '05_reports'`
- **What the bug is:** `output_root.parents[1]` resolves to `cwt-sim/` (the project root). The path `cwt-sim/05_reports` does not exist. Reports and plots are written to an auto-created `05_reports` directory at the project root rather than `cwt-sim/cgt_benchmarks/reports`.
- **Note:** This pattern is inherited from the existing phase 13 and 14 code. It was likely correct under the old `cwt_cgt/` flat layout where `05_reports` was a sibling directory to the results directory. The migration to `cwt/cgt/` under `cwt-sim/` changed the depth, but the `parents[1]` and `05_reports` literal were not updated.
- **Severity:** HIGH -- pre-existing pattern that phases 16-24 copy without correction. All report output lands in wrong directories.

## Subtle Issues

### Fragile transitive imports

- `phase19_analysis.py` line 15 imports `_build_context` and `_centered_tangent_field` from `phase18_analysis`, but phase18 does not define these -- it imports them from `phase15_analysis`. If phase18 ever removes those imports (e.g., during refactoring), phase19 will break with an `ImportError` that gives no hint about the actual source module. The same pattern occurs with `_plot_bars`, `_plot_heatmap`, `_plot_line`, and `_plot_scatter` imported transitively through phase15 by phases 16, 17, 18.

### Phase 18 operator list substitution logic

- `phase18_analysis.py` line 160: `ops = base_ops_u if len(base_ops_u) == len(ops) else ops`. This silently replaces the Lindblad operator list from `lindblad_operators()` with the analytically-constructed operator list from `_analytic_jump_tangents()` when the counts happen to match. If the counts match but the operators differ in meaning or ordering, the subsequent `_superoperator_jacobian` call will use mismatched operators and derivatives, producing numerically wrong commutator projections. The fallback (keeping original `ops`) is used when counts don't match, which could itself indicate a genuine inconsistency in the construction.

### Empty valid_mask arrays in summarize calls

- Multiple phases (16, 17, 18) pass `field['centered_field'][field['valid_mask']]` to `summarize()` and `summarize_abs()`. If all cells are untrusted (valid_mask is all False), the resulting array is empty. The `summarize` function in `geometry.py` (lines 131-145) handles this with a `size == 0` guard returning None values, so this is not a crash risk, but the downstream JSON will contain `null` fields that consumers may not expect.

## Test Gaps

- No tests were identified in the changeset for phases 16-24. The import verification passes (`from cwt.cgt.analysis.phaseN_analysis import *`), but no functional tests exist to exercise the path construction logic, the report generation, or the numerical pipelines.
- The path string issues (CRITICAL-1, CRITICAL-2, HIGH-1, HIGH-2) could be caught by a test that instantiates the payload functions against a temporary directory and asserts output files land where expected.

## Semantic Drift Risks

- The `output_root` parameter has inconsistent semantics across phases: phases 16-21 receive `cgt_benchmarks/results`, while phases 22-24 receive the project root. This split convention means that adding a new phase requires guessing which convention to follow, and a wrong guess produces silent file misdirection.
- The `05_reports` and `03_benchmarks` directory names are relics of a pre-migration layout. They are scattered across both the new phase modules and the older run scripts. The migration was incomplete -- only module-level Python imports were rewritten (`from .X` to `from ..X`), but hardcoded filesystem path strings were not updated.

## Verdict: FAIL

## Blocking Issues

1. **CRITICAL-1:** Phases 22, 23, 24 reference `03_benchmarks` directory that does not exist. Phase 22 and 23 will raise `FileNotFoundError`. Phase 24 will silently write to wrong location.
2. **CRITICAL-2:** Phases 22, 23, 24 write reports to `05_reports` which does not exist, creating a shadow output tree.
3. **HIGH-1:** Phase 17 doubles the `cgt_benchmarks` path component, writing reports to `results/cgt_benchmarks/reports/` instead of `cgt_benchmarks/reports/`.
4. **HIGH-2:** Phases 16, 18, 19, 20, 21 write reports to `cwt-sim/05_reports/` instead of `cwt-sim/cgt_benchmarks/reports/`. (Note: this is inherited from phases 13-14, but the 16-24 changeset should not ship with known-broken report paths.)

All four blocking issues must be resolved before commit. The `03_benchmarks` references must become `cgt_benchmarks`, the `05_reports` references must become `cgt_benchmarks/reports`, and the phase 17 doubled path must be corrected.
