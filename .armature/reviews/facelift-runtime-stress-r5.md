# Red Team Review: facelift-runtime-stress-r5

## Summary

Runtime stress testing of loop shapes, Lindblad functions, geometry utilities, mixed-state geometry, and analytic tangent modules. All loop shapes produce closed paths with correct winding under all tested edge cases (zero size, minimal/maximal discretization, negative centers, both orientations). Lindblad functions pass round-trip, shape, trace-preservation, and edge-case tests cleanly. One HIGH finding on Windows encoding, one MEDIUM on missing guard in `projective_metric_trace_and_curvature`, and one MEDIUM on unguarded `None` access in `analytic_tangents.py`.

## Critical Findings

None.

## High Findings

### H1: `phase15_analysis.py` line 951 -- `write_text` without `encoding='utf-8'` on Windows

- **File:** `cwt-sim/cwt/cgt/analysis/phase15_analysis.py`, line 951
- **What:** `report_path.write_text(...)` uses the platform default encoding (cp1252 on Windows), but the report contains Greek characters (chi U+03C7 on lines 863-864, gamma on lines 749, 776, 790, 873, 880, 885, 892, 900).
- **How to trigger:** Run `test_phase15_report_respects_reports_dir` on Windows, or call `phase15_report()` on any Windows machine.
- **What happens:** `UnicodeEncodeError: 'charmap' codec can't encode character '\u03c7' in position 313: character maps to <undefined>`. The test fails and no report file is written.
- **Verified:** Test failure confirmed in `python -m pytest tests/unit/test_cgt_smoke.py -x -q` (1 failed, 23 passed).
- **Severity:** HIGH -- blocks report generation on Windows; test is failing in CI-equivalent conditions.
- **Note:** Lines 607 and 681 in the same file also use `write_text` without encoding for JSON content, which currently contains only ASCII but could silently break if non-ASCII content is introduced later.

## Medium Findings

### M1: `projective_metric_trace_and_curvature` silently returns NaN when `du=0` or `dv=0`

- **File:** `cwt-sim/cwt/geometry/coherence.py`, lines 71-72
- **What:** Division by `2.0 * du` or `2.0 * dv` with no guard against zero values. When either is zero, the function returns `(nan, nan)` with only a numpy RuntimeWarning.
- **How to trigger:** `projective_metric_trace_and_curvature(psi0, psi_same, psi_same, psi_same, psi_same, du=0.0, dv=0.01)`
- **What happens:** Returns `(nan, nan)` silently. Downstream consumers that do not check for NaN will propagate invalid values.
- **Severity:** MEDIUM -- callers currently use finite step sizes, but there is no validation or documented precondition.

### M2: `analytic_tangents.py` -- unguarded `None.state` access when branch_id not found

- **File:** `cwt-sim/cwt/cgt/analytic_tangents.py`, lines 42, 68, 113, 155, 200 (all `_tangents_*` functions)
- **What:** Each `_tangents_*` function calls `benchmark.resolve_candidate_by_id(u, v, branch_id)` which returns `None` when the branch_id is not found, then immediately accesses `.state` on the result without a guard.
- **How to trigger:** `analytic_branch_tangents('benchmark_a', 'NONEXISTENT', 0.3, 0.4)` produces `AttributeError: 'NoneType' object has no attribute 'state'`.
- **What happens:** Unhelpful `AttributeError` instead of a clear error message. In practice, `phase18_analysis.py` passes correct branch IDs from the atlas, so this is not a runtime crash risk under normal usage.
- **Severity:** MEDIUM -- defensive, the error message is confusing and could waste debugging time if branch naming ever changes.

## Subtle Issues

### S1: `_polygon_loop` CW reversal keeps the first vertex fixed

`_polygon_loop` reversal logic is `[vertices[0]] + list(reversed(vertices[1:]))`. This means the first vertex is always the starting point regardless of orientation. This is correct for producing opposite-sign areas (verified), but it means the CW and CCW paths do not trace the exact same geometric locus -- they share the same start point but traverse different interpolation sequences. For polygon shapes with `steps_per_segment > 1`, the intermediate points on each segment differ between CW and CCW. This is not a bug per se, but it means CW/CCW comparisons are not perfectly symmetric at the per-point level. The overall signed areas are correct inverses.

### S2: `stadium` shape depends on `side` being large enough relative to the radius fraction

In `_stadium_loop`, `r = 0.18 * side` and `half_len = side / 2.0 - r`. When `side` is very small but nonzero (e.g., `side=0.01`), the geometry becomes extremely compressed but remains valid. When `side=0`, all points collapse to the center (verified OK). No crash, but the shape quality degrades for small `side` values.

## Test Gaps

### TG1: No existing test verifies loop shape closure for non-square shapes

The test suite tests loop behavior at the integration level (run_single_loop, run_benchmark_loops) but does not unit-test `build_loop_path` with each shape name to verify closure. This review's Phase 1 provides that coverage empirically, but it should be a permanent regression test.

### TG2: No test for `projective_metric_trace_and_curvature` with degenerate inputs

No test covers the `du=0` or `dv=0` case, or identical psi inputs. The function returns NaN silently in these cases.

### TG3: No test for `lindblad_superoperator` trace-preservation property

The Lindblad generator should satisfy trace preservation up to the depolarizing rate. No test checks this structural property.

## Semantic Drift Risks

### SD1: `LindbladConfig` vs `OpenSystemConfig` naming collision

Both `lindblad.py` and `open_system.py` define similar config dataclasses with overlapping field names but different defaults (e.g., `dt=0.02` vs `dt=0.18`, `depolarizing_rate` vs `depolarizing`). The `branch_hamiltonian` function in `open_system.py` accepts both config types via duck typing (it only reads `.coherent_scale` and `.site_potential_scale`), but the `LindbladConfig` has a `coherent_scale` of 1.05 while `OpenSystemConfig` also has 1.05 -- they happen to match today but are independently maintained.

## Verdict: PASS_WITH_ADVISORIES

## Advisories:
- **H1 (HIGH):** `phase15_analysis.py:951` must add `encoding='utf-8'` to `write_text()` calls. The test `test_phase15_report_respects_reports_dir` is currently failing on Windows.
- **M1:** `projective_metric_trace_and_curvature` should either validate `du > 0, dv > 0` or document the precondition.
- **M2:** `analytic_tangents.py` should guard `resolve_candidate_by_id` returns against `None` with a clear error message.
- **TG1:** Add unit tests for `build_loop_path` closure across all shapes.
