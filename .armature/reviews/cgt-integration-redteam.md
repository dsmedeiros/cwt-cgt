# Red Team Review: CGT Integration into cwt-sim

## Summary

The CGT integration contains **three confirmed runtime crash bugs** that affect the majority of the analysis and orchestration modules. The new geometry modules (`cwt/geometry/*.py`) and the compat shim (`_geom_compat.py`) are solid and pass tests. However, the higher-level orchestration layers -- `robustness.py`, `branch_jumps.py`, `modal_analysis.py`, `jacobian_analysis.py` -- are wired to APIs that do not exist in their current form. Specifically: (1) `run_benchmark_loops` is called with keyword arguments it does not accept, (2) `mode_wilson_phase` is called without its required `mode_index` argument, and (3) `modal_diagnostics` returns a `dict` but callers access it as if it were a dataclass with attribute access. These are not edge cases -- they are guaranteed `TypeError`/`AttributeError` crashes on any invocation of the affected modules. The 46 tests pass but only exercise the compat shim and basic geometry; they do not touch any of the broken code paths.

**Verdict: FAIL**

---

## Critical Findings

### CRITICAL-1: `run_benchmark_loops` does not accept `protocol_name` or `filename` kwargs

- **File and line:** `cwt-sim/cwt/cgt/loop_protocols.py:232` (function definition)
- **What:** `run_benchmark_loops(benchmark_id, output_root, config)` has exactly three parameters. Multiple callers pass `protocol_name=` and/or `filename=` keyword arguments.
- **How to trigger:** Call any of these callers:
  - `robustness.py:116-122` -- `run_benchmark_loops(..., protocol_name=protocol.name, filename=protocol.filename)`
  - `jacobian_analysis.py:242` -- `run_benchmark_loops(..., protocol_name=..., filename=...)`
  - `jacobian_analysis.py:327` -- `run_benchmark_loops(..., protocol_name=..., filename=...)`
  - `modal_analysis.py:149` -- `run_benchmark_loops(..., protocol_name=...)`
  - `modal_analysis.py:222` -- `run_benchmark_loops(..., protocol_name=...)`
- **What happens:** `TypeError: run_benchmark_loops() got an unexpected keyword argument 'protocol_name'`
- **Blast radius:** The entire robustness suite, all Jacobian analysis pipelines, and all modal analysis pipelines are dead on arrival. This blocks `run_robustness_suite`, `jacobian_loop_payload`, `patchwise_jacobian_explanation`, `modal_loop_payload`, `patchwise_modal_explanation`, and all their transitive callers.
- **Severity:** CRITICAL

### CRITICAL-2: `mode_wilson_phase` called without required `mode_index` argument

- **File and line:** `cwt-sim/cwt/cgt/modal.py:108` (function definition requires `mode_index: int`)
- **What:** Every call site passes only `frames` without `mode_index`:
  - `jacobian_analysis.py:163` -- `mode_wilson_phase(frames)`
  - `jacobian_analysis.py:264` -- `mode_wilson_phase(frames)`
  - `modal_analysis.py:97` -- `mode_wilson_phase(local_frames)`
  - `modal_analysis.py:156` -- `mode_wilson_phase(frames)`
  - `modal_analysis.py:233` -- `mode_wilson_phase(frames)`
- **How to trigger:** Any of the above call sites.
- **What happens:** `TypeError: mode_wilson_phase() missing 1 required positional argument: 'mode_index'` -- confirmed by runtime test.
- **Severity:** CRITICAL

### CRITICAL-3: `modal_diagnostics` returns a `dict` but `modal_analysis.py` accesses it with attribute syntax

- **File and line:** `cwt-sim/cwt/cgt/modal.py:86-94` (returns dict), `cwt-sim/cwt/cgt/analysis/modal_analysis.py:69-74` (accesses as attributes)
- **What:** `modal_diagnostics(frame)` returns `{"spectral_gap": ..., "biorthogonality_error": ..., "dominant_eigenvalue": ..., "dominant_eigenvalue_abs": ..., "inverse_gap": ...}`. But `modal_analysis.py:71-74` does:
  ```python
  gap_map[i, j] = diag.spectral_gap          # AttributeError
  inverse_gap_map[i, j] = diag.inverse_gap_proxy   # AttributeError + wrong key name
  biorthogonality_map[i, j] = diag.biorthogonality_error  # AttributeError
  dominant_phase_map[i, j] = diag.dominant_phase    # AttributeError + key doesn't exist
  ```
- **Additional key mismatch:** Even if the dict were converted to an object, the key is `inverse_gap` not `inverse_gap_proxy`, and `dominant_phase` does not exist at all (only `dominant_eigenvalue` and `dominant_eigenvalue_abs` exist).
- **How to trigger:** Call `modal_scan_payload()`.
- **What happens:** `AttributeError: 'dict' object has no attribute 'spectral_gap'` -- confirmed by runtime test.
- **Severity:** CRITICAL

### HIGH-1: `branch_jumps.py` accesses nonexistent keys on loop and scan payloads

- **File and line:** `cwt-sim/cwt/cgt/branch_jumps.py:25-44`
- **What:** The module accesses keys that neither `run_benchmark_loops` nor `run_benchmark_scan` produce:
  - `pair['pair_r4']` -- does not exist in `_pair_summary` output
  - `pair['switch_count_total']` -- does not exist
  - `pair['net_branch_jump_difference']` -- does not exist
  - `pair['excluded_reason']` -- does not exist
  - `pair['ccw']['unique_branch_ids']` -- does not exist in `run_single_loop` output
  - `pair['ccw']['branch_dwell_fractions']` -- does not exist
  - `scan_payload['branch_continuation']` -- does not exist in `run_benchmark_scan` output
- **How to trigger:** Call `branch_jump_payload()`.
- **What happens:** `KeyError` on the first missing key access.
- **Severity:** HIGH (entire module is non-functional)

---

## Subtle Issues

### S-1: `_geom_compat.overlap()` semantics differ from a hypothetical reference `overlap()`

The compat shim's `overlap(psi_a, psi_b)` computes `|<a|b>|` (modulus of inner product), which is the fidelity for pure states. The underlying `psi.inner()` uses `np.vdot(z, w)` which conjugates the first argument. This is standard physics convention and the cross-validation test confirms correctness. No regression found.

### S-2: `lindblad.py:28` passes `LindbladConfig` to `branch_hamiltonian(state, config: OpenSystemConfig)`

Both dataclasses have `coherent_scale` and `site_potential_scale` attributes, so duck typing works today. But if `OpenSystemConfig` gains a new field that `branch_hamiltonian` uses, `LindbladConfig` will silently produce wrong results because its field won't be present. This is a composition seam risk.

### S-3: `polygon_signed_area` in `berry.py:49-56` does not close the polygon

The loop iterates `zip(path[:-1], path[1:])` but does not include the closing segment from `path[-1]` to `path[0]`. For callers that append the first point at the end of the path (as `_square_loop` does at line 34), this is correct. But the function's docstring says "signed area of a polygon given as a list of (x, y) vertices" which implies an implicitly closed polygon. If any caller passes a non-repeated-endpoint polygon, the area will be wrong. The current callers are safe.

### S-4: `coherence.py:30` `wrap_phase` scalar detection

`np.isscalar(values)` returns `False` for numpy 0-d arrays and some numeric types that users might pass. If a numpy scalar (`np.float64(1.5)`) is passed, `np.isscalar` returns `True` in numpy < 2.0 but `False` in numpy >= 2.0. Since the project requires numpy >= 1.24, this is a potential numpy-version-dependent behavioral difference. The consequence is returning a 0-d array instead of a float, which is usually harmless but could surprise callers doing `isinstance(..., float)` checks.

### S-5: `mixed_state.py:97-101` `polar_unitary` returns identity for rank-deficient input

If the input matrix has all singular values below `tol=1e-12`, the function returns `np.eye(matrix.shape[0])`. This is a reasonable fallback but it means `uhlmann_link_unitary` returns identity when both density matrices are near-zero, which could silently produce zero holonomy instead of flagging a degenerate geometry. The `mixed_loop_holonomy_phase` function already handles the zero-trace case (line 123-124), so the overall pipeline degrades gracefully.

### S-6: `_fit_through_origin` is duplicated 6 times

The function `_fit_through_origin` appears in `loop_protocols.py`, `noisy.py`, `jacobian_analysis.py`, `modal_analysis.py`, `phase10_analysis.py`, `phase11_analysis.py`, and `phase12_analysis.py` with minor variations. Most are identical, but `phase12_analysis.py:86` uses `max(np.dot(xs, xs), 1e-15)` while others use bare `np.dot(xs, xs)`. Also, `stats.py:44` provides a canonical `fit_through_origin` that returns `{"slope": ..., "r_squared": ...}` (note `r_squared` not `r2`), so none of the callers use it. This creates six maintenance copies that can drift independently.

---

## Test Gaps

### TG-1: No tests for any module above the compat shim layer

The 46 tests cover:
- Benchmark instantiation (5 benchmarks)
- `run_benchmark_scan` output keys and file creation
- Branch atlas ambiguity for benchmark F
- Phase alignment helpers
- Compat shim `overlap` vs `inner`
- `psi_from_parts` unit norm
- `density_from_state` properties (trace, hermiticity, PSD)
- Bures distance self-distance
- Fidelity self-fidelity and symmetry

**Not tested at all:**
- `loop_protocols.run_benchmark_loops`
- `loop_protocols.run_single_loop`
- `continuation.continue_path_with_branch_ids`
- `open_system.*` (any function)
- `lindblad.*` (any function)
- `noisy.*` (any function)
- `jacobian.*` (any function)
- `modal.*` (any function, including the broken `mode_wilson_phase`)
- `topology.*` (any function)
- `robustness.*` (any function)
- `branch_jumps.*` (any function)
- `reporting.*` (any function)
- `plotting.*` (any function)
- All five analysis modules

If any of the above had even a single smoke test, the CRITICAL bugs would have been caught.

### TG-2: No negative/edge-case tests for `mixed_state.py`

- No test for `matrix_sqrt_psd` on a near-singular matrix
- No test for `project_to_density` on a matrix with all-negative eigenvalues
- No test for `unwrap_phase_sequence` with a single element
- No test for `polar_unitary` fallback path
- No test for `mixed_loop_holonomy_phase` with fewer than 2 matrices

### TG-3: No test for `berry_loop_flux` with fewer than 2 states

The function returns 0.0 for `len(psi_states) < 2`, but no test exercises this path.

### TG-4: No integration test that verifies benchmark C produces a positive signed-loop law

The benchmarks are analytic constructions. There is no test verifying that the ring benchmark actually produces the expected nonzero curvature and sign-flip fraction, which is the primary scientific claim of the benchmark framework.

---

## Semantic Drift Risks

### SD-1: `robustness.py._evaluate_payload` logic is dead code for off-center protocols

The function checks `protocol_name.startswith('offcenter_')` (line 76), but `protocol_name` is read from `summary.get('protocol_name', '')`. Since `run_benchmark_loops` never puts `protocol_name` in the summary (it doesn't accept that parameter), `protocol_name` is always `''`, and the off-center evaluation branch is never reached. The off-center evaluation logic exists but can never fire.

### SD-2: The `reporting.py` module references keys that don't exist in scan or loop payloads

`branch_continuation`, `excluded_pair_count`, `persistent_branch_counts`, and `switch_tile_count` are referenced via `.get()` so they don't crash, but they always return empty/None values. The reports will show "No branch atlas metadata recorded." for every benchmark.

---

## Category Verdicts

| # | Category | Verdict | Notes |
|---|----------|---------|-------|
| 1 | Import integrity | **PASS** | No stale `from .geometry import` or `from .mixed_state_geometry import` found. All CGT modules correctly use `from ._geom_compat import` or `from cwt.geometry.mixed_state import`. |
| 2 | GEOM-001 violations | **PASS** | No geometry module imports from `layers/`, `orchestrator/`, `experiments/`, or `baselines/`. |
| 3 | Deduplication in noisy.py | **PASS** | All formerly inlined density-matrix functions are replaced by imports from `cwt.geometry.mixed_state`. `observable_operator` remains in `open_system.py` (single location). No duplicate definitions of the seven target functions remain in the cgt package. |
| 4 | Three reconstructed functions in modal.py | **FAIL** | `modal_diagnostics` returns a `dict` but all callers use attribute access. Additionally, callers reference keys (`inverse_gap_proxy`, `dominant_phase`) that don't match the actual dict keys (`inverse_gap`, not present). |
| 5 | Analysis module import paths | **PASS** | All `from ..X import Y` paths resolve correctly. The `from .._geom_compat import` usage is correct throughout. |
| 6 | Silent regressions from import rewiring | **PASS** | The compat shim's `overlap()` correctly delegates to `psi.inner()` and takes the absolute value. Cross-validation tests confirm equivalence. |
| 7 | Edge cases in mixed_state.py | **PASS with advisories** | `unwrap_phase_sequence` handles empty arrays correctly. `matrix_sqrt_psd` clamps negative eigenvalues. `polar_unitary` has a reasonable fallback. No crash-grade edge case bugs found, but no tests exercise these paths. |
| 8 | Test coverage gaps | **FAIL** | Tests cover only the geometry/compat layer (roughly 15% of new code by module count). The entire upper half of the stack is untested, which is how the three CRITICAL bugs survived. |
| 9 | pyproject.toml | **PASS** | Dependencies are reasonable. `matplotlib>=3.7` covers the plotting module. `scipy>=1.10` covers any future use. No missing runtime deps detected. The `cgt_benchmarks` lint exclusion is correctly configured. |
| 10 | Other issues | **FAIL** | `run_benchmark_loops` API mismatch crashes 5+ call sites. `branch_jumps.py` is entirely non-functional due to missing payload keys. |

---

## Verdict: FAIL

## Blocking Issues:

1. **CRITICAL-1:** `run_benchmark_loops` does not accept `protocol_name` or `filename` kwargs. Five call sites will crash with `TypeError`. Either add these parameters to the function signature or remove them from callers.

2. **CRITICAL-2:** `mode_wilson_phase(frames, mode_index)` requires `mode_index` but all five call sites omit it. Either make `mode_index` default to `0` (or to `frame.dominant_index`) or add it at every call site.

3. **CRITICAL-3:** `modal_diagnostics` returns a `dict` but `modal_analysis.py` accesses attributes. Either change it to return a dataclass/namedtuple, or change callers to use bracket access. Also fix the key name mismatches (`inverse_gap_proxy` should be `inverse_gap`, and `dominant_phase` needs to be added or derived from `dominant_eigenvalue`).

4. **HIGH-1:** `branch_jumps.py` references at least seven payload keys that do not exist. The entire module is non-functional.

5. **Test coverage:** The test suite does not exercise any code above the compat shim. At minimum, add smoke tests for `run_single_loop`, `run_benchmark_loops`, and `mode_wilson_phase` to prevent regressions of this class.
