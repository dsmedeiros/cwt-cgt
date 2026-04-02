# Red Team Review: facelift-adversarial-runtime-r5

## Summary

Round 5 adversarial runtime testing of phases 35, 38, and 39 reveals a systematic crash vulnerability across all 10 analysis modules (phases 30-39) when `_augment_rows` receives derivation parameters with `None` values, an `OverflowError` crash on adversarial but mathematically possible input combinations, missing key guards, and stale path references in older analysis phases and scripts. The happy path works correctly and deterministically; the bugs are all on defensive-coding edge cases that become reachable if upstream data shape changes or if a benchmark level has no trusted pairs.

## Critical Findings

### C1. `_augment_rows` crashes with `TypeError: float() argument must be a string or a real number, not 'NoneType'` when derivation has None parameters (ALL phases 30-39)

- **Files:** `cwt-sim/cwt/cgt/analysis/phase{30..39}_analysis.py`, each in `_augment_rows`
- **Specific lines:** phase39 line 82-84, phase38 line 95-97, phase35 line 114-118 (analogous lines in all others)
- **What:** Each `derive_*` function returns `None` for aggregated parameter values when the train set is empty (no trusted pairs). The corresponding `_augment_rows` function immediately calls `float(params['mean_variance_alignment'])` (or equivalent) without checking for `None`. This crashes with `TypeError`.
- **How to trigger:** Call `derive_local_superoperator_compactness_normalizer([], level_block)` then pass the result and any non-empty row list to `_augment_rows`.
- **What happens:** Unhandled `TypeError` crash. The analysis function cannot complete.
- **Blast radius:** If any dephasing level in a source artifact has zero trusted pairs in the train partition, the entire analysis chain crashes.
- **Reproduced:** Yes, confirmed via runtime execution.
- **Severity:** HIGH -- crashes on valid (if unlikely) input; prevents graceful degradation.

### C2. `OverflowError` in phase39 `_augment_rows` line 95 on adversarial but numerically reachable inputs

- **File:** `cwt-sim/cwt/cgt/analysis/phase39_analysis.py`, line 95
- **What:** The expression `(mean_variance_alignment / max(float(row['variance_alignment']), eps)) ** local_compactness_exponent` can overflow when `variance_alignment` is near `eps` (1e-12) and `share_geometry` is large. The base becomes ~1e12 and the exponent is proportional to `share_geometry`, yielding exponentiation overflow.
- **How to trigger:** Set `row['variance_alignment'] = 1e-13` and `row['share_geometry'] = 100.0`.
- **What happens:** `OverflowError: (34, 'Result too large')` -- unhandled crash.
- **Reproduced:** Yes, confirmed via runtime execution.
- **Severity:** HIGH -- crash on extreme but valid numerical input; no guard or clamp on the exponent.

### C3. Unbounded predictor amplification when `variance_alignment = 0.0`

- **File:** `cwt-sim/cwt/cgt/analysis/phase39_analysis.py`, line 95
- **What:** When `variance_alignment = 0.0`, the eps guard limits the denominator to `1e-12`, but the resulting ratio (~7.8 billion for typical mean_variance_alignment values) propagates through to the predictor, producing a predictor value of `-205,477` -- orders of magnitude outside normal range.
- **How to trigger:** Set `row['variance_alignment'] = 0.0`.
- **What happens:** Silently produces wildly wrong predictions that corrupt downstream statistics (R2, correlations).
- **Severity:** CRITICAL -- wrong output produced silently, no clamp on the compactness ratio.

## Subtle Issues

### S1. Inconsistent `_safe_float` wrapping in `switch_metrics` across phases 30-39

- **Files:** Phases 30-36 write raw `None` values to `switch_metrics` dict entries; phases 37-39 wrap them with `_safe_float()` converting `None` to `NaN`.
- **Impact:** Consumers of the `switch_metrics` payload must handle both `null` (JSON) and `NaN` (JSON number) representations of missing R2, depending on which phase produced the artifact. This is a semantic drift between older and newer phases. Not a crash, but a fragile contract.

### S2. `min(levels, ...)` on empty `levels` list

- **Files:** All phases 30-39, at the `switch_level = min(levels, ...)` line (e.g., phase39 line 220)
- **Impact:** If the source payload has an empty `levels` list, `min()` raises `ValueError`. This is an unguarded edge case. While unlikely with valid artifacts, it would produce an unhelpful traceback.

### S3. Missing key access in `_augment_rows` for trusted rows

- **Files:** All phases 30-39
- **Impact:** `_augment_rows` accesses row keys like `local_area_share`, `share_geometry`, `variance_alignment` etc. via `row['key']` without `.get()` or any guard. If any trusted row is missing an expected key, the function crashes with `KeyError`. The `trusted_pair` check is necessary but not sufficient -- a row could be trusted but have an incomplete field set.

### S4. Stale `03_benchmarks` and `05_reports` path references

- **Files:** `cwt-sim/scripts/cgt/generate_reports.py` (line 20-21), `cwt-sim/scripts/cgt/run_benchmark.py` (line 14), `cwt-sim/scripts/cgt/run_loops.py` (line 21), `cwt-sim/scripts/cgt/run_modal_analysis.py` (lines 13-14), `cwt-sim/scripts/cgt/run_phase{10..15}_analysis.py`, `cwt-sim/scripts/cgt/run_robustness.py` (line 19), `cwt-sim/cwt/cgt/analysis/phase{10..15}_analysis.py`
- **Impact:** These 17 files reference `03_benchmarks/` and `05_reports/` directories that do not exist on disk. The current layout uses `cgt_benchmarks/results/` and `cgt_benchmarks/reports/`. Running any of these older scripts or analysis functions would fail with `FileNotFoundError`.

### S5. Duplicate `normalize_probabilities` implementation

- **Files:** `cwt-sim/cwt/geometry/coherence.py` (line 15) and `cwt-sim/cwt/cgt/geometry.py` (line 9)
- **Impact:** Two independent copies of the same function. If one is updated, the other silently diverges. The `_geom_compat.py` shim already re-exports from `cwt.geometry.coherence`, so `cwt.cgt.geometry` is a redundant copy. Currently only consumed by `tests/unit/test_facelift_utilities_redteam.py`.

## Test Gaps

1. **No test for empty train partition.** None of the analysis phases (30-39) are tested with a dephasing level containing zero trusted pairs. This would trigger C1.
2. **No test for extreme numerical inputs.** No tests feed `variance_alignment = 0.0`, `local_area_share = 0.0`, or near-eps values to `_augment_rows`. This would trigger C2 and C3.
3. **No test for missing row keys.** No tests verify behavior when a trusted row is missing expected fields.
4. **No negative test for empty levels list.** No test checks that the analysis functions fail gracefully (or at all) with an empty `levels` array in the source payload.
5. **No integration test for the phase37->38->39 chain.** The chain works (verified in this review), but there is no automated test for it.

## Semantic Drift Risks

1. **`_safe_float` inconsistency** between phases creates a moving contract for downstream consumers (see S1).
2. **Stale path layout** in phases 10-15 and scripts means the older analysis pipeline is silently broken. Anyone running `scripts/cgt/run_phase10_analysis.py` would get a crash with no obvious explanation.
3. **The eps guard pattern** (`max(value, 1e-12)`) prevents division by zero but allows astronomically large intermediate values that corrupt predictions silently (C3). The guard creates a false sense of safety.

## Verdict: PASS_WITH_ADVISORIES

## Advisories:

- **A1 (HIGH):** C1 -- `_augment_rows` in phases 30-39 must handle `None` derivation parameters without crashing. Either early-return when params contain `None`, or skip augmentation for the level.
- **A2 (HIGH):** C2 -- The exponentiation in phase39 (and similar patterns in phase37/38) must clamp the exponent or use a safe exponentation wrapper to prevent `OverflowError`.
- **A3 (CRITICAL):** C3 -- The compactness ratio produced when `variance_alignment` is near zero must be clamped to prevent silently producing wildly wrong predictions. The eps guard alone is insufficient.
- **A4 (MEDIUM):** S4 -- The 17 files with stale `03_benchmarks`/`05_reports` paths should be updated or removed.
- **A5 (LOW):** S5 -- The duplicate `normalize_probabilities` in `cwt/cgt/geometry.py` should be removed in favor of the canonical `cwt/geometry/coherence.py` version.
