# Red Team Review Round 2: Float Guards, Phase 28, Geometry

## Summary

Three Round 1 findings were re-examined. Two of three are fully resolved. One remains: the `normalize_probabilities` empty-array fix was applied only to `cwt/cgt/geometry.py` but not to the second copy at `cwt/geometry/coherence.py`, which still crashes with `ZeroDivisionError` on empty input. A new consistency issue was also identified in phase29 switch_metrics serialization (MEDIUM, non-blocking).

## Critical Findings

### FINDING-1: ZeroDivisionError in cwt/geometry/coherence.py:normalize_probabilities (CRITICAL)

- **File and line:** `cwt-sim/cwt/geometry/coherence.py`, line 21
- **What the bug is:** When `values` is an empty array, `arr.size` is 0. The code reaches `1.0 / arr.size`, causing `ZeroDivisionError`.
- **How to trigger:** `from cwt.geometry.coherence import normalize_probabilities; import numpy as np; normalize_probabilities(np.array([]))`
- **What happens:** Unhandled `ZeroDivisionError` crashes the caller.
- **Note:** The identical function in `cwt/cgt/geometry.py` (line 11-12) was correctly patched with an early return for empty arrays. The fix was not propagated to this second copy.
- **Severity:** CRITICAL

## Subtle Issues

### Phase 29 switch_metrics writes raw None for corr/sign_agreement

- **File:** `cwt-sim/cwt/cgt/analysis/phase29_analysis.py`, lines 206-207
- **Issue:** `corr` and `sign_agreement` values from `_prediction_summary` (which can return `None` for these fields) are placed directly into the switch_metrics dict without `_safe_float` wrapping. Phases 37 and 39 wrap the same pattern with `_safe_float`. This is safe for JSON serialization (`None` becomes `null`) but inconsistent. If any future consumer calls `float()` on these JSON values, it will fail on `null`.
- **Severity:** MEDIUM

## Resolved Findings from Round 1

1. **Float guards (phases 30-39):** RESOLVED. All phase files 29-39 define `_safe_float(v) -> float` which maps `None` to `float('nan')`. All `r2`, `corr`, and `sign_agreement` values that feed into downstream numeric computation are wrapped. Bare `float(level['dephasing'])` calls are safe because `dephasing` is a required numeric input parameter, never None.

2. **Phase 28 artifact filename:** RESOLVED. `phase28_analysis.py` line 408 writes to `benchmark_c_phase28_generator_geometry_share.json`. `phase29_analysis.py` line 16 (Phase29Config) reads from `benchmark_c_phase28_generator_geometry_share.json`. Names match.

3. **Geometry normalize_probabilities (cwt/cgt/geometry.py):** RESOLVED in this copy. Empty-array guard at lines 11-12 returns early. Confirmed by running `normalize_probabilities(np.array([]))` which returns `[]` without error.

## Test Gaps

- No test covers `cwt.geometry.coherence.normalize_probabilities` with an empty array. The smoke tests (64 passed) do not exercise this path.
- No test covers phase29 switch_metrics when `heldout_combined_fit` returns all-None fields.

## Semantic Drift Risks

- Two copies of `normalize_probabilities` exist (`cwt/cgt/geometry.py` and `cwt/geometry/coherence.py`) with divergent behavior. This is a maintenance hazard beyond the immediate bug.

## Verdict: FAIL

## Blocking Issues:
- FINDING-1: `cwt/geometry/coherence.py:normalize_probabilities` crashes with `ZeroDivisionError` on empty input. The fix applied to `cwt/cgt/geometry.py` must also be applied here.
