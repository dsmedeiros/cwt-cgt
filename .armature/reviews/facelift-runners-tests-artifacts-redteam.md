# Red Team Review: facelift-runners-tests-artifacts

## Summary

The changeset introduces 24 runner scripts (phases 16-39), one smoke test file with 41 test cases, and 24 benchmark artifact JSON files. All 41 tests pass. However, the tests are shallow -- they verify file existence, JSON validity, and import success but do not exercise any runtime behavior. Three analysis modules (phases 22, 23, 24) contain hardcoded stale `03_benchmarks` paths that would produce `FileNotFoundError` at runtime, and the tests cannot catch this because they only test importability, not invocation. Several runner scripts reference a nonexistent `05_reports` directory. The artifact JSON files contain stale `03_benchmarks/` path prefixes in their `source_phaseXX_artifact` metadata fields. None of these issues are caught by the current test suite.

## Critical Findings

### C1: Hardcoded stale `03_benchmarks` path in phase 22, 23, 24 analysis modules (HIGH)

- **Files and lines:**
  - `cwt-sim/cwt/cgt/analysis/phase22_analysis.py` line 135: `results_root = project_root / '03_benchmarks' / 'results'`
  - `cwt-sim/cwt/cgt/analysis/phase23_analysis.py` line 77: `results_root = project_root / '03_benchmarks' / 'results'`
  - `cwt-sim/cwt/cgt/analysis/phase24_analysis.py` line 218: `results_root = project_root / '03_benchmarks' / 'results'`
- **What the bug is:** These three analysis modules construct file paths using `03_benchmarks` as a directory component, but the actual directory in the repository is `cgt_benchmarks`. Any call to `phase22_payload()`, `phase23_payload()`, or `phase24_payload()` will attempt to read from a nonexistent path.
- **How to trigger it:** Call `phase22_payload(project_root=Path("cwt-sim"))` from the repository root.
- **What happens when triggered:** `FileNotFoundError` is raised at runtime because `cwt-sim/03_benchmarks/results/benchmark_C_ring/` does not exist.
- **Severity:** HIGH -- These are runtime failures on valid invocation, not theoretical edge cases. The test suite's importability check (which passes) masks this completely because the stale path is inside a function body, not at module scope.

NOTE: These modules are outside the declared changeset scope (phases 16-39 new files), but they are directly imported and invoked by runner scripts within scope (run_phase22_analysis.py, run_phase23_analysis.py, run_phase24_analysis.py) and covered by the test file under review.

## Subtle Issues

### S1: Stale `03_benchmarks` path metadata in all phase 22-39 artifact JSON files

Every artifact from phase 22 onward contains `source_phaseXX_artifact` values like:
```
"source_phase38_artifact": "03_benchmarks/results/benchmark_C_ring/benchmark_c_phase38_..."
```
The actual filesystem path is `cgt_benchmarks/results/...`. These paths are informational metadata (computed at artifact-generation time via `relative_to(project_root)`) and are not used for runtime file loading. However, any downstream tool or human that attempts to resolve these paths will fail. This is semantic drift -- the metadata no longer reflects reality.

### S2: Runner scripts 16, 18, 19, 21 reference nonexistent `05_reports` directory

- `cwt-sim/scripts/cgt/run_phase16_analysis.py` line 12: references `project_root / "05_reports"` in a print statement (no mkdir, would not crash but prints a wrong path)
- `cwt-sim/scripts/cgt/run_phase18_analysis.py` lines 27-29: creates `05_reports` directory and writes `phase18_summary.json` into it
- `cwt-sim/scripts/cgt/run_phase19_analysis.py` lines 13-16: creates `05_reports` directory and writes `phase19_summary.json` into it
- `cwt-sim/scripts/cgt/run_phase21_analysis.py` line 13: writes to `05_reports` path

These scripts would create an `05_reports` directory that is not in the repository structure and appears to be a stale artifact from a previous directory layout. The correct reports path appears to be `cgt_benchmarks/reports/`.

### S3: IMPORTABLE_PHASES is unnecessarily conservative

The test file comment (lines 60-63) claims phases 16 and 18-21 "may require optional external data at import time." Verified by running `importlib.import_module` on all excluded phases (16, 17, 18, 19, 20, 21, 23, 24): all 8 import successfully without error. The exclusion list is wider than necessary, reducing test coverage without justification.

### S4: Inconsistent API naming across analysis modules

Runner scripts import two different naming conventions:
- Phases 16-28: `phaseXX_payload` functions
- Phases 29-39: `run_phaseXX_analysis` functions

This is not a bug but creates a maintenance hazard and makes it harder to write generic tooling across phases.

## Test Gaps

### T1: Tests do not verify runtime invocability

The importability test (`test_phase_analysis_module_importable`) only proves that `import cwt.cgt.analysis.phaseXX_analysis` succeeds. It does not call any function. The stale `03_benchmarks` path in phases 22-24 (Finding C1) is completely invisible to this test because the bug is inside a function body, not at module scope. An adversarial test would attempt to invoke the public entry point with the project root and verify it does not raise.

### T2: `test_phase39_artifact_structure` does not check `switch_metrics`

The test checks for `{"phase", "benchmark", "verdict"}` but omits `switch_metrics`, which is present in all phase 25-39 artifacts and is a key structural element. The test cannot distinguish a phase 39 artifact that has full switch_metrics from one that is missing them entirely.

### T3: No schema consistency test across phases

There is no test verifying that artifacts sharing the same schema family (e.g., phases 25-39 which all have `switch_metrics`, `switch_level`, `slug`, etc.) actually share consistent top-level keys. A single artifact with a typo in a key name or a missing field would pass all current tests.

### T4: No test for phase chain integrity

The artifacts encode a phase chain via `source_phaseXX_artifact` keys. No test verifies that:
- Each phase N (where applicable) references phase N-1
- The referenced artifact filename actually exists on disk
- The `source_phaseXX_artifact` path uses the correct directory prefix

### T5: No negative tests

There are no tests for error conditions: what happens if an artifact file is missing, empty, or malformed? What if an analysis module is deleted? The current tests only verify the happy path with pre-existing data.

### T6: Phases 21 and 24 have no predecessor reference in artifacts

The phase chain check revealed:
- Phase 21: no `source_phase20_*` key
- Phase 24: no `source_phase23_*` key

These may be intentional branch points in the analysis chain, but the absence is undocumented and untested.

## Semantic Drift Risks

### D1: Old-style scripts (phases 10-15) use `sys.path` hacks and `03_benchmarks`/`04_code` paths

The older runner scripts (`run_phase10_analysis.py` through `run_phase15_analysis.py`, plus `generate_reports.py`, `run_benchmark.py`, etc.) contain `sys.path.insert(0, str(SRC_ROOT))` hacks and reference `03_benchmarks` and `04_code` directories. The new scripts (phases 16-39) correctly avoid `sys.path` manipulation and mostly use `cgt_benchmarks`, but the coexistence of both patterns creates confusion about which convention is authoritative. The three exceptions in phases 22-24 (Finding C1) appear to be a half-completed migration.

### D2: `parents[2]` resolution is correct but fragile

All runner scripts use `Path(__file__).resolve().parents[2]` to find the cwt-sim root. This resolves correctly from `scripts/cgt/run_phaseXX_analysis.py` (depth 2 = cwt-sim). However, if any script is moved to a different depth (e.g., `scripts/cgt/subdir/`), the resolution silently points to the wrong directory. There is no validation that the resolved path is actually the cwt-sim root (e.g., by checking for `pyproject.toml`).

## Verdict: PASS_WITH_ADVISORIES

The new runner scripts (phases 16-39), test file, and artifacts are structurally sound. Tests pass. The PHASE_SUFFIX mapping is correct for all 24 phases. The imports in runner scripts match their corresponding analysis modules. The `parents[2]` resolution is correct. No `sys.path` hacks exist in the new scripts. No `cwt_cgt` or `04_code` references exist in the new scripts.

The stale `03_benchmarks` paths in phase 22-24 analysis modules (C1) are the most serious finding, but these modules are pre-existing code outside the declared changeset scope. The current changeset did not introduce these bugs.

## Advisories:

1. **[HIGH] Fix stale `03_benchmarks` paths in phase 22, 23, 24 analysis modules.** These are runtime-broken. Even though they are pre-existing, the test file under review covers them (phase 22 is in IMPORTABLE_PHASES) and creates a false impression that they work. File a follow-up task.
2. **[MEDIUM] Add `switch_metrics` to `test_phase39_artifact_structure` required keys.** The current test verifies less than the artifact's actual contract requires.
3. **[MEDIUM] Add a parametrized test verifying common top-level keys (`phase`, `benchmark`, `verdict`, `slug`) exist in all phase 16-39 artifacts**, not just phase 39.
4. **[MEDIUM] Expand IMPORTABLE_PHASES to include phases 16-21, 23, 24.** All import successfully; the exclusion reduces coverage for no demonstrated reason.
5. **[LOW] Fix `05_reports` path references in runner scripts 16, 18, 19, 21.** These should use `cgt_benchmarks/reports/` to match the current directory structure.
6. **[LOW] Document the stale `03_benchmarks` prefix in artifact `source_phaseXX_artifact` metadata fields as known technical debt, or regenerate the artifacts with correct paths.
