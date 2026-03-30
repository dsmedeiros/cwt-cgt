# Red Team Review: cgt-integration-redteam-pass3

## Summary

Third-pass red team review. The HIGH-2 fix (protocol_name sourcing) is confirmed correct. All 46 unit tests pass. However, two new issues were found: one CRITICAL (offcenter robustness protocols can never pass due to a missing summary key) and one HIGH (benchmark_f crashes on loop execution due to unhandled observable type). The user-provided robustness verification script fails because the test payload was incomplete for the offcenter codepath, but even with a complete payload the underlying data-flow bug prevents offcenter protocols from ever passing in production.

## Critical Findings

### CRITICAL-4: Offcenter robustness protocols for benchmark_c can never pass

- **File:** `cwt-sim/cwt/cgt/robustness.py` lines 74-91
- **What:** The offcenter evaluation path reads `summary.get('fit_response_vs_signed_flux_by_center', [])` (line 74). However, `run_benchmark_loops()` in `loop_protocols.py` does NOT produce a `fit_response_vs_signed_flux_by_center` key in its summary dict (lines 280-290). The key simply does not exist.
- **How to trigger:** Call `run_robustness_suite('benchmark_c', output_root)`. The two offcenter protocols (offcenter_square, offcenter_circle) will always evaluate to `passed=False` because `center_fits` is always `[]`, making `center_signs` empty, `consistent_sign` False, and the conjunction at line 91 always False.
- **What happens:** The robustness suite silently reports that offcenter protocols fail even when the underlying geometry is strongly positive. The `suite_passed` flag in the robustness output will always be False for benchmark_c if any offcenter protocol is included. This corrupts downstream acceptance decisions.
- **Severity:** CRITICAL -- silent wrong result on a core evaluation path.

### HIGH-3: benchmark_f crashes when run through loop protocols

- **File:** `cwt-sim/cwt/cgt/loop_protocols.py` lines 85-107 (`_primary_value`)
- **What:** `benchmark_f` declares `primary_observable='final_p4'` (benchmarks.py line 244). The `_primary_value` function only handles `final_p1`, `final_p3`, `mean_position`, and `excess_circulation`. It raises `ValueError('Unsupported observable: final_p4')` for benchmark_f.
- **How to trigger:** `run_benchmark_loops('benchmark_f', output_root)` or any code path that calls it (e.g., `branch_jump_payload('benchmark_f', ...)`, `run_benchmark_all('benchmark_f', ...)`, phase 11/12 analysis for benchmark_f).
- **What happens:** Unhandled ValueError crash. The `open_system.py:observable_operator` handles `final_p4` correctly, so this is an omission only in `_primary_value`.
- **Severity:** HIGH -- crash on valid input for a defined benchmark.

## Subtle Issues

### Missing `excluded_pair_count` in loop summary

- **File:** `cwt-sim/cwt/cgt/reporting.py` line 95 reads `loop_summary.get('excluded_pair_count')`, but `run_benchmark_loops` does not produce this key in its summary dict.
- **Impact:** Reports will display "Excluded pair count: None" instead of the actual count. Not a crash (uses `.get()`), but incorrect report output.
- **Severity:** MEDIUM

### Dead R4 regime check in `_pair_summary`

- **File:** `cwt-sim/cwt/cgt/loop_protocols.py` line 218
- **What:** `classify_loop_regime` only returns 'R1', 'R2', or 'R3'. The check `ccw['regime_label'] == 'R4'` in `_pair_summary` is dead code. The `pair_r4` flag is only set by the `switch_count_total > 0` arm.
- **Impact:** No wrong results, but the code is misleading. If R4 detection were added to `classify_loop_regime` in the future, the behavior would change silently.
- **Severity:** LOW

## Test Gaps

1. **No test exercises `run_benchmark_loops` for benchmark_f.** The crash from HIGH-3 would have been caught by a simple smoke test.
2. **No test exercises `run_robustness_suite` end-to-end.** The CRITICAL-4 silent failure would have been caught by asserting that at least one offcenter protocol can pass with appropriate data.
3. **No test verifies the summary keys produced by `run_benchmark_loops` against what downstream consumers (reporting, robustness, branch_jumps) expect.** A schema-contract test would catch the `excluded_pair_count` gap and the `fit_response_vs_signed_flux_by_center` gap.
4. The user-provided robustness verification script in this review is misleading: it constructs a synthetic payload with the `fit_response_vs_signed_flux_by_center` key that real `run_benchmark_loops` output never contains. The script should use actual `run_benchmark_loops` output to be a valid integration test.

## Semantic Drift Risks

- The `_fit_through_origin` function is duplicated in at least 6 files (loop_protocols.py, jacobian_analysis.py, modal_analysis.py, phase10_analysis.py, phase11_analysis.py, phase12_analysis.py, noisy.py). Each has slightly different return type annotations and one (phase12) adds a `max()` guard on the denominator. A future fix to one copy will silently leave the others unfixed.

## Verdict: FAIL

## Blocking Issues:

- **CRITICAL-4:** `run_benchmark_loops` does not produce `fit_response_vs_signed_flux_by_center` in its summary, so offcenter robustness protocols for benchmark_c always evaluate to `passed=False`. Either the key must be added to the loop summary, or the offcenter evaluation logic must be changed to use data that actually exists.
- **HIGH-3:** `_primary_value` in `loop_protocols.py` does not handle `final_p4`, causing benchmark_f to crash on any loop-protocol execution path. A `final_p4` branch must be added.
