# Red Team Review: facelift-final-redteam-r3

## Summary

Round 3 verification of the two Round 2 blocking issues: (1) `normalize_probabilities` empty-array crash and (2) `phase29_analysis.py` unguarded `switch_metrics` values. Both fixes are confirmed correct. However, the test suite now has a new failure introduced by the fix itself -- an `xfail(strict=True)` marker that was not removed after the bug was resolved. One pre-existing test failure (UTF-8 encoding, `test_phase15_report_respects_reports_dir`) is unrelated to this changeset.

## Critical Findings

None. The two Round 2 blocking issues are resolved.

## Verification Results

### Issue 1: `normalize_probabilities` empty-array guard

**coherence.py (line 18-19):** Guard is correctly placed before any arithmetic. Verified via direct invocation:
- `np.array([])` returns empty array (no crash)
- `np.array([0.0, 0.0])` returns `[0.5, 0.5]` (uniform fallback works)
- `np.array([1.0, 2.0, 3.0])` returns correct normalisation

**geometry.py (line 11-12):** The duplicate implementation in `cwt/cgt/geometry.py` also has the identical guard applied. Both copies are now consistent.

**_geom_compat.py:** The CGT module shim routes `normalize_probabilities` imports to `cwt.geometry.coherence` (the canonical copy), so the `cwt.cgt.geometry` copy is only used by code that imports it directly (the test file).

### Issue 2: `phase29_analysis.py` switch_metrics

**Lines 202-207:** All six values in the `switch_metrics` dict are wrapped in `_safe_float()`:
- `phase28_heldout_new_r2`
- `phase28_heldout_combined_r2`
- `phase29_heldout_new_r2`
- `phase29_heldout_combined_r2`
- `phase29_heldout_combined_corr`
- `phase29_heldout_combined_sign_agreement`

The `_safe_float` helper (line 20) converts `None` to `float('nan')` and all other values to `float`. This is correct -- JSON serialisation handles NaN via the default encoder, and downstream consumers that read these values will get a numeric type rather than crashing on None.

### Duplicate implementation check

`grep -rn "def normalize_probabilities"` found exactly two definitions:
1. `cwt/geometry/coherence.py:15` -- canonical, fixed
2. `cwt/cgt/geometry.py:9` -- duplicate, also fixed

No other copies exist.

## Subtle Issues

### 1. Stale xfail marker in test (causes test failure)

- **File:** `tests/unit/test_facelift_utilities_redteam.py`, line 112
- **What:** `@pytest.mark.xfail(reason="BUG: geometry.py:14 divides by arr.size=0", raises=ZeroDivisionError, strict=True)`
- **Problem:** The test was written when `cwt.cgt.geometry.normalize_probabilities` still had the empty-array bug. Now that the bug is fixed, the test passes unexpectedly. Because `strict=True`, pytest reports this as `XPASS(strict)` which counts as a FAIL.
- **Impact:** The test suite reports 2 failures. One of these (`test_empty_array`) is a false alarm caused by the stale marker. The xfail marker must be removed (or replaced with a normal assertion) now that the fix is in place.
- **Severity:** HIGH -- the test suite cannot pass cleanly until this is addressed.

### 2. Pre-existing encoding failure (not from this changeset)

- **File:** `tests/unit/test_cgt_smoke.py::test_phase15_report_respects_reports_dir`
- **What:** `UnicodeEncodeError: 'charmap' codec can't encode character '\u03c7'` (Greek letter chi) when writing report to disk on Windows with cp1252 locale.
- **Impact:** Pre-existing, not introduced by this changeset. Not blocking for this review.

## Test Gaps

None introduced by this changeset. The existing test coverage for `normalize_probabilities` (all-zeros, negatives, single element, empty array) is adequate.

## Semantic Drift Risks

The dual implementation of `normalize_probabilities` in both `cwt.geometry.coherence` and `cwt.cgt.geometry` is a maintenance liability. They are currently identical, but future edits to one copy could silently diverge from the other. The `_geom_compat` shim mitigates this for CGT-internal consumers, but the `cwt.cgt.geometry` copy is still directly imported by the test file.

## Verdict: FAIL

## Blocking Issues:

- `tests/unit/test_facelift_utilities_redteam.py:112` -- The `@pytest.mark.xfail(strict=True)` on `TestNormalizeProbabilities.test_empty_array` must be removed or converted to a normal passing test. The fix it was written against has been applied; the stale marker now causes a hard test failure (`XPASS(strict)`). The test suite cannot pass cleanly until this is resolved.
