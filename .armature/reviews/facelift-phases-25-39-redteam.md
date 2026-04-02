# Red Team Review: facelift-phases-25-39

## Summary

Fifteen phase analysis modules (25-39) were reviewed end-to-end. The modules
are structurally consistent and follow a clear chain pattern. All imports
succeed and the existing smoke test suite passes. However, there is one
critical artifact-chain filename mismatch that will silently break the
pipeline on re-run, and a systematic unguarded `float(None)` pattern across
phases 30-39 that will crash on edge-case input data. Neither defect is
currently exercised because the existing on-disk artifacts happen to be
well-formed, but both are latent regressions waiting to trigger.

## Critical Findings

### C1: Phase 28 output filename does not match Phase 29 input filename
- **File:** `cwt-sim/cwt/cgt/analysis/phase28_analysis.py`, line 408
- **What:** `phase28_payload()` writes to `benchmark_c_phase28_generator_geometry_normalization.json`
- **Expected by consumer:** `phase29_analysis.py` line 16 and `test_cgt_phase16_to_39_smoke.py` line 46 both expect `benchmark_c_phase28_generator_geometry_share.json`
- **How to trigger:** Run `phase28_payload(project_root)`. The output file will be `benchmark_c_phase28_generator_geometry_normalization.json`. Then run `run_phase29_analysis(project_root)` -- it will raise `FileNotFoundError` because it looks for `benchmark_c_phase28_generator_geometry_share.json`.
- **Why tests pass today:** The old artifact `benchmark_c_phase28_generator_geometry_share.json` already exists on disk from a prior run. The smoke test only checks file existence and JSON validity, not whether the current code produces the correct filename.
- **Severity:** CRITICAL -- re-running phase 28 breaks the entire chain from phase 29 onward.

### C2: Unguarded float(None) on source-level R2 values in phases 30-39
- **Files:** All of `phase30_analysis.py` through `phase39_analysis.py`
- **What:** Lines like `phase29_new_r2.append(float(level['heldout_new_fit']['r2']))` call `float()` on a value that can be `None` (when `_prediction_summary` returns `r2: None` for empty or constant-response trusted sets).
- **How to trigger:** Feed a source artifact where any level has `heldout_new_fit.r2 == null` or `heldout_combined_fit.r2 == null`. This raises `TypeError: float() argument must be a string or a real number, not 'NoneType'`.
- **Contrast:** Phases 25-28 correctly use `float('nan') if ... is None else float(...)` guards for the same pattern.
- **Severity:** HIGH -- valid input data causes a crash rather than graceful degradation. Currently masked because all on-disk artifacts happen to have non-null R2 values.

### C3: Unguarded float(None) on switch_metrics corr/sign_agreement in phases 37-39
- **Files:** `phase37_analysis.py` lines 264-265, `phase38_analysis.py` lines 277-278, `phase39_analysis.py` lines 266-267
- **What:** `float(switch_level['heldout_combined_fit']['corr'])` and `float(switch_level['heldout_combined_fit']['sign_agreement'])` crash when these values are `None`.
- **How to trigger:** Supply data where the held-out combined set has fewer than 2 trusted rows, or all yhat/y are constant. `_prediction_summary` returns `corr: None`.
- **Severity:** HIGH -- same pattern as C2, but also affects the switch-metrics output block.

## Subtle Issues

### S1: Dead code and misleading assignment in phase31 _augment_rows
- **File:** `phase31_analysis.py`, line 131
- **What:** `beta_boundary = float(... if False else 0.0)` is dead code -- the `if False` branch is never taken. Line 134 then reassigns `beta_boundary` from `derivation['beta_boundary']`. The dead code is confusing and suggests an incomplete refactor.
- **Risk:** LOW -- functionally harmless because line 134 overwrites it.

### S2: Missing mkdir for artifact and summary outputs in phases 25-28
- **Files:** `phase25_analysis.py` line 262-263, line 273; `phase26_analysis.py` line 329, 340; `phase27_analysis.py` line 378, 400; `phase28_analysis.py` line 408, 430
- **What:** These phases write to `bench_dir / filename` and `reports / summary.json` without calling `mkdir(parents=True, exist_ok=True)` on the parent directory. Phases 29-39 correctly do this.
- **Risk:** MEDIUM -- if the directories don't pre-exist (e.g., fresh clone without artifact checkout), these phases will crash with `FileNotFoundError`.

### S3: Inconsistent API surface between phase groups
- **What:** Phases 25-28 define `phaseXX_payload(project_root, config)` with no `output_root` parameter. Phases 29-39 define `run_phaseXX_analysis(project_root, output_root, config)` and some alias it as `phaseXX_payload`. Phase 29 has no alias at all. Phases 37, 38, 39 have no `phaseXX_payload` alias.
- **Risk:** LOW -- affects programmatic consumers who expect a uniform API.

### S4: Baseline coefficients passed as float|None without enforcement
- **What:** `derive_moment_derived_higher_order_coefficients` (phase 25, line 51) calls `float(baseline_coefficients['m2_gap'])` where the type annotation allows `None`. If a caller passes a dict with None coefficient values alongside a non-empty trusted set, this crashes.
- **Risk:** LOW -- in practice the baseline coefficients are always populated when trusted rows exist.

## Test Gaps

1. **No test exercises the chain end-to-end.** The smoke test checks artifact existence and importability but never calls `phaseXX_payload()` or `run_phaseXX_analysis()`. The filename mismatch (C1) is invisible to it.
2. **No test feeds None-R2 data into phases 30-39.** A simple parametrized test that constructs a source artifact with `r2: null` in one level would catch C2.
3. **No test for fresh-directory execution.** Running any phase 25-28 payload function on a fresh `project_root` without pre-existing `cgt_benchmarks/results/` would expose S2.
4. **No negative test for missing source artifact.** Phases 25-28 have explicit `FileNotFoundError` raises; phases 29-39 rely on the implicit `FileNotFoundError` from `read_text()`. No test verifies either path.

## Semantic Drift Risks

1. **_prediction_summary is duplicated 15 times.** Every file contains an identical copy. A bug fix or enhancement to one copy must be manually replicated to all 14 others. This is a maintenance time bomb. A shared utility would eliminate this risk.
2. **The phase 28 filename divergence** suggests a rename happened in the code but not in the test or in the consumer (phase 29). If additional phases are added that reference phase 28, they may copy either the old or new name, creating further drift.

## Verdict: FAIL

## Blocking Issues:
- **C1:** Phase 28 output filename `benchmark_c_phase28_generator_geometry_normalization.json` does not match the expected input filename `benchmark_c_phase28_generator_geometry_share.json` used by phase 29 and the smoke test. Re-running phase 28 breaks the chain.
- **C2:** Phases 30-39 will crash with `TypeError` if any source artifact level has `r2: null`. The `float('nan') if ... is None else float(...)` guard used in phases 25-28 must be applied consistently.
- **C3:** Phases 37-39 switch_metrics blocks will crash with `TypeError` if `corr` or `sign_agreement` is `None`.
