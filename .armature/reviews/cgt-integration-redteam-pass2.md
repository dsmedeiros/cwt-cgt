# Red Team Review (Pass 2): CGT Integration into cwt-sim

## Summary

All four blocking issues from the first red team review (3 CRITICAL, 1 HIGH) have been fixed and verified both by code inspection and by runtime execution. The fixes are structurally sound: `run_benchmark_loops` now accepts `protocol_name` and `filename` kwargs; `mode_wilson_phase` defaults `mode_index` to 0; `modal_diagnostics` returns a frozen `ModalDiagnostics` dataclass with all expected attributes including `inverse_gap_proxy` and `dominant_phase`; and `run_single_loop`, `_pair_summary`, and `run_benchmark_scan` all now emit the keys required by `branch_jumps.py`. All 180 tests pass. No circular import issues were found.

One new HIGH-severity bug was discovered: `robustness.py:_evaluate_payload` reads `protocol_name` from the wrong location in the payload dict, causing the off-center evaluation logic for benchmark_c to silently never activate.

**Verdict: PASS_WITH_ADVISORIES**

---

## Fix Verification

### CRITICAL-1: `run_benchmark_loops` signature -- FIXED

**Evidence:**
- `loop_protocols.py:251` now reads: `def run_benchmark_loops(benchmark_id: str, output_root: Path, config: LoopConfig | None = None, protocol_name: str | None = None, filename: str | None = None) -> dict:`
- All 7 call sites verified compatible:
  - `robustness.py:116-122` -- passes `protocol_name` and `filename`. Matches.
  - `jacobian_analysis.py:242` -- passes `protocol_name` and `filename`. Matches.
  - `jacobian_analysis.py:327` -- passes `protocol_name` and `filename`. Matches.
  - `modal_analysis.py:149` -- passes `protocol_name` only. Matches (filename defaults to None).
  - `modal_analysis.py:222` -- passes `protocol_name` only. Matches.
  - `runner.py:166` -- passes neither. Matches (both default to None).
  - `scripts/cgt/run_loops.py:24-28` -- passes neither. Matches.
  - `branch_jumps.py:21` -- passes neither. Matches.
- `protocol_name` is stored at `payload['protocol_name']` (line 299).
- `filename` controls the output filename (line 320-321), defaulting to `{benchmark_id}_loops.json`.

**Verdict: PASS**

### CRITICAL-2: `mode_wilson_phase` default -- FIXED

**Evidence:**
- `modal.py:119` now reads: `def mode_wilson_phase(frames: list[ModalFrame], mode_index: int = 0) -> float:`
- All 5 call sites pass only `frames` without `mode_index`:
  - `jacobian_analysis.py:163` -- `mode_wilson_phase(frames)`
  - `jacobian_analysis.py:264` -- `mode_wilson_phase(frames)`
  - `modal_analysis.py:97` -- `mode_wilson_phase(local_frames)`
  - `modal_analysis.py:156` -- `mode_wilson_phase(frames)`
  - `modal_analysis.py:233` -- `mode_wilson_phase(frames)`
- Default of 0 (dominant mode) is semantically appropriate.
- Runtime test confirms: `mode_wilson_phase([frame, frame])` returns without error.

**Verdict: PASS**

### CRITICAL-3: `modal_diagnostics` return type -- FIXED

**Evidence:**
- `modal.py:86-94` defines `ModalDiagnostics` as a `@dataclass(frozen=True)` with fields: `spectral_gap`, `inverse_gap_proxy`, `dominant_phase`, `biorthogonality_error`, `dominant_eigenvalue`, `dominant_eigenvalue_abs`.
- `modal.py:96-105` `modal_diagnostics(frame)` returns a `ModalDiagnostics` instance.
- `modal_analysis.py:71-74` accesses `diag.spectral_gap`, `diag.inverse_gap_proxy`, `diag.biorthogonality_error`, `diag.dominant_phase` -- all present on the dataclass.
- Runtime test confirms: `hasattr(diag, 'spectral_gap')`, `hasattr(diag, 'inverse_gap_proxy')`, `hasattr(diag, 'dominant_phase')` all True.

**Verdict: PASS**

### HIGH-1: `branch_jumps.py` missing keys -- FIXED

**Evidence:**

`run_single_loop` (loop_protocols.py:179-204) now returns:
- `switch_count` (line 200) -- sourced from `continuation['switch_count']`
- `unique_branch_ids` (line 202) -- sourced from `continuation['unique_branch_ids']`
- `branch_dwell_fractions` (line 203) -- computed from `branch_ids_list`

`_pair_summary` (loop_protocols.py:207-238) now returns:
- `pair_r4` (line 218, 232)
- `switch_count_total` (line 217, 233)
- `net_branch_jump_difference` (line 234)
- `excluded_reason` (line 219, 235)

`run_benchmark_scan` (runner.py:116-129) now returns `branch_continuation` dict with:
- `persistent_branch_counts` (line 117-119)
- `chosen_branch_counts` (line 120-123)
- `switch_tile_count` (line 125)
- `ambiguous_tile_count` (line 126)
- `residual_summary` (line 127)
- `ambiguity_score_summary` (line 128)

`branch_jumps.py` accesses all of these at lines 25-44 and 49-54. All keys match.

Runtime test confirms: `run_single_loop` result contains `switch_count`, `unique_branch_ids`, `branch_dwell_fractions`; `run_benchmark_scan` result contains `branch_continuation` with all four expected sub-keys.

**Verdict: PASS**

---

## New Findings

### HIGH-2: `robustness.py:_evaluate_payload` reads `protocol_name` from wrong location

- **File and line:** `cwt-sim/cwt/cgt/robustness.py:67`
- **What:** `protocol_name = summary.get('protocol_name', '')` reads from `payload['summary']`, but `run_benchmark_loops` stores `protocol_name` at `payload['protocol_name']` (loop_protocols.py:299), not inside the `summary` sub-dict.
- **Consequence:** `protocol_name` is always `''`. The condition at line 76 (`benchmark_id == 'benchmark_c' and protocol_name.startswith('offcenter_')`) is never true. Off-center protocols for benchmark_c silently fall through to the generic benchmark_c evaluation at line 93-95, which uses a global fit instead of the intended center-wise fit logic.
- **Additionally:** Line 74 reads `center_fits = summary.get('fit_response_vs_signed_flux_by_center', [])`. The `summary` dict (loop_protocols.py:280-290) does not contain `fit_response_vs_signed_flux_by_center`, so even if the off-center path were reached, `center_fits` would be `[]`, `valid_centers` would be empty, `consistent_sign` would be False, and the off-center protocol would always fail evaluation.
- **How to trigger:** Call `run_robustness_suite('benchmark_c', ...)`. The off-center protocols will be evaluated using the generic benchmark_c criteria instead of the center-wise criteria.
- **Blast radius:** The robustness suite for benchmark_c will still run without crashing, but the evaluation logic for 2 of 4 protocols (offcenter_square, offcenter_circle) uses the wrong criteria. The scientific conclusion about off-center spatial robustness is unreliable.
- **Severity:** HIGH

### MEDIUM-1: `classify_loop_regime` never returns 'R4' but `_pair_summary` checks for it

- **File and line:** `cwt-sim/cwt/cgt/loop_protocols.py:110-115` (returns R1/R2/R3 only), line 218 (checks for 'R4')
- **What:** `classify_loop_regime` can only return 'R1', 'R2', or 'R3'. The check `ccw['regime_label'] == 'R4'` at line 218 is dead code. The `pair_r4` flag is effectively determined solely by `switch_count_total > 0`.
- **Consequence:** No functional bug today -- `switch_count_total > 0` is the correct detection mechanism for branch switching. But the variable name `pair_r4` and the dead 'R4' comparison create semantic confusion. Benchmark F has `expected_regime='R4'` (benchmarks.py:240) but `classify_loop_regime` never produces that label.
- **Severity:** MEDIUM (semantic drift risk, no wrong output currently)

### MEDIUM-2: `reporting.py:_branch_summary_text` now works but `evaluate_benchmark` lacks the enriched criteria

- **File and line:** `cwt-sim/cwt/cgt/reporting.py:54-61`
- **What:** `_branch_summary_text` reads `scan.get('branch_continuation', {})` which now exists (HIGH-1 fix). This function will now produce real output instead of the previous "No branch atlas metadata recorded." However, `evaluate_benchmark` at line 29-51 does not incorporate any branch-continuation data into its pass/fail logic. The branch atlas enrichment is cosmetic in reporting but not used for verdicts.
- **Severity:** MEDIUM (not a bug, but the enriched data is underutilized)

### MEDIUM-3: `_fit_through_origin` duplicated 7 times with diverging implementations

- **File and line:** `loop_protocols.py:241`, `noisy.py`, `jacobian_analysis.py:28`, `modal_analysis.py:28`, `phase10_analysis.py:40`, `phase11_analysis.py:57`, `phase12_analysis.py:83`
- **What:** Seven copies of the same function. Six use `np.dot(xs, xs)` as the denominator; `phase12_analysis.py:86` uses `max(np.dot(xs, xs), 1e-15)`. If any one copy gets a bugfix, the others remain stale.
- **Severity:** MEDIUM (maintenance risk)

---

## Subtle Issues

### S-1: `_pair_summary` R4 excluded_reason text is misleading when switch_count > 0 but no actual R4 regime

When `switch_count_total > 0` but both runs have regime R1 or R2, the `excluded_reason` reads "R4 branch switching". This labels the pair as R4 even though the regime classification never produced R4. The text should arguably read "branch switching detected" without the R4 label.

### S-2: `run_single_loop` computes `branch_dwell_fractions` from `branch_ids_list` which includes the repeated start point

At line 35, `path.append(path[0])` closes the loop. The continuation at line 126 processes all path points including this repeat. This means the closing point is counted in branch dwell fractions. For loops that do not switch branches, this inflates the dwell of the closing branch by one step. The effect is small (1/N where N = path length) and consistent across comparisons, so it does not affect relative measurements.

### S-3: `continue_path_with_branch_ids` potential off-by-one in switch detection

At line 264, a switch is detected when `previous_branch_id is not None and choice.candidate.branch_id != previous_branch_id`. The very first step (index 0) never triggers a switch because `previous_branch_id` starts as None. The closing step (last point = first point repeated) could trigger a spurious switch if the continuation picks a different branch at the same coordinates due to different reference states. This is a boundary effect, not a crash bug.

---

## Test Gaps

### TG-1: No test for `run_robustness_suite`

The off-center evaluation bug (HIGH-2) would be caught by a test that runs `run_robustness_suite('benchmark_c', ...)` and checks that off-center protocols use center-wise evaluation.

### TG-2: No test for `branch_jump_payload`

Now that HIGH-1 is fixed, `branch_jump_payload` should work end-to-end, but no test verifies this.

### TG-3: No test for `modal_scan_payload` or `modal_loop_payload`

These use the fixed `modal_diagnostics` and `mode_wilson_phase`, but no test verifies the full pipeline.

### TG-4: No negative test for `run_single_loop` with a benchmark that has branch switching

Benchmark F is designed for switching. A test that runs `run_single_loop` on benchmark_f and verifies `switch_count > 0` and `len(unique_branch_ids) > 1` would validate the enrichment under the intended conditions.

---

## Verdict: PASS_WITH_ADVISORIES

All four first-pass blocking issues are confirmed fixed and verified by both code inspection and runtime execution. The 180-test suite passes cleanly.

## Advisories:

1. **HIGH-2 (robustness off-center evaluation):** `robustness.py:67` reads `protocol_name` from `payload['summary']` instead of `payload['protocol_name']`. The off-center evaluation logic for benchmark_c is dead code. This should be fixed before relying on robustness suite verdicts for benchmark_c spatial robustness claims. Additionally, `fit_response_vs_signed_flux_by_center` is not present in the summary dict, so even after fixing the protocol_name lookup, the center-wise fit data would need to be computed and added to the summary or payload.

2. **MEDIUM-1 (R4 semantic drift):** `classify_loop_regime` never returns 'R4', but code and labels reference it. Consider either adding R4 to the classifier (when `switch_count > 0`) or removing the R4 references from `_pair_summary`.

3. **MEDIUM-3 (duplicated `_fit_through_origin`):** Seven diverging copies of the same function. Consider extracting to a shared utility.

4. **Test coverage:** The CGT upper-stack modules (robustness, branch_jumps, modal_analysis, jacobian_analysis) still lack any test coverage. Smoke tests for these would prevent regression of the class of bugs found in the first review.
