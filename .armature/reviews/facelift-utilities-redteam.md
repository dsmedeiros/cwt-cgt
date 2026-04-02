# Red Team Review: facelift-utilities

## Summary

The changeset adds well-structured utility functions across five files in `cwt-sim/cwt/cgt/`. The new loop shapes all produce valid closed paths with correct orientation reversal. The Lindblad superoperator and its Frechet derivative are numerically consistent (verified via finite differencing). Import chains are clean -- no GEOM-001 violations detected. However, there is one confirmed crash bug in `geometry.py`, one latent mathematical error in `lindblad_superoperator_frechet` that happens to be masked by the scaffold's use of real-valued operators, and one silent data corruption path in `projective_metric_trace_and_curvature`. None of these block the commit given their actual triggering conditions in this codebase, but the `geometry.py` crash is a genuine edge-case defect.

## Critical Findings

None at CRITICAL severity. No wrong-output bugs were found that can be triggered by the existing benchmark pipelines or test suites.

## Subtle Issues

### 1. `geometry.py` line 14: ZeroDivisionError on empty array -- MEDIUM

- **File:** `cwt-sim/cwt/cgt/geometry.py`, line 14
- **What:** `normalize_probabilities` divides by `arr.size` when sum is zero, but if the input array is empty (`arr.size == 0`), this is a division by zero.
- **How to trigger:** `normalize_probabilities(np.array([]))`
- **What happens:** `ZeroDivisionError: float division by zero`
- **Actual risk:** Low. Empty probability arrays are unlikely in practice since all BranchState objects have at least n=2 nodes. Confirmed via adversarial test (`test_empty_array` marked xfail).
- **Severity:** MEDIUM

### 2. `lindblad_superoperator_frechet` lines 127-128: transposed anti-commutator terms -- MEDIUM

- **File:** `cwt-sim/cwt/cgt/lindblad.py`, lines 127-128
- **What:** The Frechet derivative of the anti-commutator part uses `kron(ident, da.T) + kron(da, ident)` but the mathematically correct expression (matching the convention in `lindblad_superoperator`) is `kron(ident, da) + kron(da.T, ident)`. The `da` and `da.T` are swapped between the two Kronecker terms.
- **Why it does not matter today:** All jump operators produced by `lindblad_operators` and `lindblad_operator_family` are real-valued (they are sparse matrices with real `sqrt(rate)` entries). For real operators, `da` is real symmetric, so `da = da.T` identically. Numerical verification with finite differencing confirms the output matches to ~1e-9 relative error.
- **What would break:** If anyone introduces complex-valued jump operators (e.g., for modeling coherent tunneling or spin-orbit coupling), the Frechet derivative would silently produce wrong results.
- **Severity:** MEDIUM (latent -- correct today, wrong in a plausible future extension)

### 3. `geometry.py` line 77: silent NaN on zero step size -- MEDIUM

- **File:** `cwt-sim/cwt/cgt/geometry.py`, line 77
- **What:** `projective_metric_trace_and_curvature` divides `(psi_plus - psi_minus)` by `2.0 * du`. When `du=0.0`, numpy produces `inf` or `nan` silently (with a RuntimeWarning) rather than raising. The function returns NaN values without any guard.
- **How to trigger:** Call with `du=0.0` or `dv=0.0`.
- **Actual risk:** Low. Callers always pass finite step sizes derived from grid spacing.
- **Severity:** MEDIUM

### 4. `lindblad_superoperator_frechet` silently truncates mismatched list lengths -- LOW

- **File:** `cwt-sim/cwt/cgt/lindblad.py`, line 123
- **What:** `zip(operators_center, doperators)` will silently truncate if the two lists have different lengths. The function does not validate that `len(operators_center) == len(doperators)`.
- **Actual risk:** Very low. The only caller (`phase17_analysis.py`) constructs both lists from the same `lindblad_operator_family` output, guaranteeing equal length.
- **Severity:** LOW

### 5. Code duplication between `cwt.cgt.mixed_state_geometry` and `cwt.geometry.mixed_state`

- **Files:** `cwt-sim/cwt/cgt/mixed_state_geometry.py` vs `cwt-sim/cwt/geometry/mixed_state.py`
- **What:** The new `mixed_state_geometry.py` duplicates several functions (`density_from_state`, `project_to_density`, `matrix_sqrt_psd`, `fidelity`, `bures_distance_sq`, etc.) that already exist in `cwt/geometry/mixed_state.py`. The implementations are functionally identical (confirmed via testing). Meanwhile, `lindblad.py` imports from `cwt.geometry.mixed_state` (the original), and `mixed_state_geometry.py` imports `psi_from_state` from `.geometry` (the new cgt copy).
- **Risk:** If one copy is updated and the other is not, they will silently diverge. This is a maintenance burden, not a bug.
- **Severity:** LOW (semantic drift risk)

## Test Gaps

1. **No existing tests for `lindblad_superoperator`, `lindblad_operator_family`, or `lindblad_superoperator_frechet`.** The adversarial test suite added in this review covers basic shape, trace preservation, and zero-perturbation. A finite-difference consistency test between the superoperator and its Frechet derivative should be added to the permanent test suite.

2. **No tests for `second_magnus_projection` or `third_order_path_projection` with non-commuting operators.** The current tests only verify the early-return guards and commuting-operator trivial cases. Tests with genuinely non-commuting superoperators would verify the mathematical structure.

3. **No tests for `analytic_tangents.py` at all.** This module contains substantial analytic derivative computations for five different benchmark families. None of them are tested against finite-difference verification. This is the largest untested surface in the changeset.

4. **The `_secondary_value` function's `edge_current_23` branch (loop_protocols.py line 228) uses `math.sqrt(p[1] * p[2])` without guarding against negative products.** While probabilities should be non-negative, a defensive `max(0.0, ...)` guard would be appropriate.

## Semantic Drift Risks

1. **`geometry.py` duplicates `_geom_compat.py` re-exports.** The new `cwt.cgt.geometry` module reimplements functions that `_geom_compat.py` already re-exports from `cwt.geometry.*`. If callers within `cwt.cgt` start importing from `cwt.cgt.geometry` instead of `cwt.cgt._geom_compat`, the two import paths will create maintenance confusion about which is canonical.

2. **`mixed_state_geometry.py` imports `psi_from_state` from `.geometry` (the new cgt copy)**, while `lindblad.py` imports density matrix functions from `cwt.geometry.mixed_state` (the original). This creates a fragmented dependency graph where the cgt module partially depends on its own geometry copy and partially on the upstream geometry package.

## Verdict: PASS_WITH_ADVISORIES

## Advisories:
- **A1:** Fix the `normalize_probabilities` empty-array crash in `geometry.py` line 14. Add a guard `if arr.size == 0: return arr` before the fallback division.
- **A2:** Add a code comment to `lindblad_superoperator_frechet` noting that the anti-commutator Frechet terms rely on jump operators being real-valued, and that the formula needs correction (`kron(ident, da)` not `kron(ident, da.T)`) if complex operators are ever introduced.
- **A3:** Add finite-difference validation tests for `analytic_tangents.py` -- this is the largest untested surface in the changeset.
- **A4:** Consider consolidating the `cwt.cgt.geometry` / `cwt.cgt.mixed_state_geometry` duplicates to re-export from the canonical `cwt.geometry.*` modules (similar to what `_geom_compat.py` does) rather than maintaining parallel implementations.
