# Code Review: Major Issues in Logic, Flow, Structure, and Theory

This document catalogues the major issues found during a comprehensive review
of the CWT-CGT codebase, spanning the Python simulation toolkit (`cwt-sim/`),
the orchestration layer, geometry estimators, layer dynamics, metrics, and
experiment drivers.

---

## 1. Parallel Transport Chain Breaks the Wilson Loop Phase

**Severity:** High · **Category:** Theory / Logic
**File:** `cwt-sim/cwt/geometry/curvature.py:35–48, 113–116`

`_parallel_transport_chain` rephases each state relative to its *predecessor*
in a sequential chain (0→i→ij→j).  The curvature is then extracted from the
Wilson loop phase around the plaquette 0→i→ij→j→0.  But parallel transport
along the chain *removes* the gauge-invariant Berry phase that the Wilson loop
is supposed to measure — the chain gauge forces every consecutive overlap to be
real and non-negative, which zeroes out the accumulated geometric phase for
well-overlapping states.  The closing leg j→0 reintroduces it, but the result
is numerically fragile and conceptually mismatched with the standard Wilson
loop prescription, which computes `arg(⟨0|i⟩⟨i|ij⟩⟨ij|j⟩⟨j|0⟩)` using the
*original* (un-rephased) states.

**Proposed fix:** The `use_pt_gauge` default should be `False` for curvature
computation.  PT gauge alignment is appropriate for the *metric* (where you
project out the gauge-dependent phase to isolate the real part of the quantum
geometric tensor), but for curvature you want the raw Wilson loop product.  If
a PT-stabilised variant is desired, it should rephase each state relative to a
*single* reference (`Psi0`) rather than chaining.

---

## 2. `biorth_curvature` Ignores Half Its Inputs

**Severity:** High · **Category:** Logic
**File:** `cwt-sim/cwt/operator/biorth_geom.py:29–42`

The function signature is `biorth_curvature(A_i, A_j, dA_i, dA_j)`, computing
`Ω_ij = ∂_i A_j − ∂_j A_i`.  But the implementation on line 41 computes
`curvature = dAi - dAj` — it uses `dA_i` and `dA_j` but completely discards
`A_i` and `A_j`.  The Berry curvature formula `∂_i A_j − ∂_j A_i` requires
`dA_i = ∂_j A_i` (the *cross*-derivative), meaning `dA_i` must be the
derivative of `A_i` with respect to `j`.  If the caller passes same-direction
derivatives, the result is meaningless.  The naming convention is ambiguous and
the API provides no guidance, making incorrect usage likely.

**Proposed fix:** Rename parameters to make the cross-derivative structure
explicit, e.g. `d_j_A_i` and `d_i_A_j`, and document the expected semantics.
Alternatively, accept a full 2×2 derivative matrix and compute the curl
internally.

---

## 3. `run_parameter_loop` Mutates the Caller's `init_state`

**Severity:** Medium · **Category:** Side-Effect Bug
**File:** `cwt-sim/cwt/orchestrator/scheduler.py:964`

`init_state.last_lambda = lambda_state` mutates the `LayersState` object
passed in by the caller on every iteration.  This leaks internal state back
through an input parameter.  Callers who reuse the same `init_state` across
multiple runs will see stale `last_lambda` values from a prior run, and there
is no documentation that the function modifies its input.

**Proposed fix:** Copy `init_state` at the top of the function, or store
`last_lambda` in the returned `RunRecord` instead of on the input.

---

## 4. Trajectory Length Mismatch Between `psi_traj` and `pQ_traj`/`theta_traj`

**Severity:** Medium · **Category:** Logic
**File:** `cwt-sim/cwt/orchestrator/scheduler.py:886–954`

`pQ_traj` and `theta_traj` are appended at line 886–887 (before FS guard
logic), but `psi_traj` is appended at line 954 (after the guard).  Both start
with one initial entry, so after the loop `len(psi_traj)` can differ from
`len(pQ_traj)` depending on early-abort conditions.  This trajectory length
mismatch will confuse downstream consumers that expect aligned arrays.

**Proposed fix:** Append to `psi_traj` at the same point as the other
trajectories, or document the offset explicitly in `RunRecord`.

---

## 5. Massive Memory Accumulation from Unbounded Trajectory Storage

**Severity:** Medium · **Category:** Structure
**File:** `cwt-sim/cwt/orchestrator/scheduler.py:586–596`

Every step appends full copies of `pQ`, `theta`, `psi_current`, `Gamma`, and
`phase_kick` arrays.  For a large substrate (N = 10,000+) with a long
parameter path (steps = 10,000), this stores ~5 × N × steps float64 values ≈
4 GB.  There is no downsampling, windowing, or checkpoint cadence.

**Proposed fix:** Add a `snapshot_interval` parameter to `RunConfig` so that
full state is recorded every k-th step, while only lightweight scalars are
tracked per step.  Alternatively, stream trajectories to disk incrementally.

---

## 6. `curvature_anytime` Fallback Has Systematic Positive-Curvature Bias

**Severity:** Medium · **Category:** Logic / Theory
**File:** `cwt-sim/cwt/geometry/adapt_mesh.py:139–179`

When no samples pass the `s_min` overlap threshold, the fallback path groups
attempts by sign and selects the group with the highest total overlap weight.
The `_group_score` function's third tiebreaker (`sign == 1`) introduces a
systematic positive-curvature bias into the fallback estimator — the code
*prefers* positive curvature over negative curvature when overlap quality is
tied.

**Proposed fix:** Remove the sign preference tiebreaker (it has no physical
justification).  Weight fallback selection purely by overlap quality, or
return NaN with a diagnostic flag when no samples meet the overlap threshold.

---

## 7. `normalize_prob` Silently Swallows Negative Values

**Severity:** Medium · **Category:** Logic
**File:** `cwt-sim/cwt/layers/state.py:54, 62`

`np.maximum(arr, 0.0)` silently clamps all negative entries to zero before
normalisation.  If the input has negative entries due to numerical instability
or a bug upstream (e.g. an unchecked geometric bias), this function masks the
problem.  The fallback to a uniform distribution when `total <= 0.0` further
hides pathological states where all probability mass has gone negative.

**Proposed fix:** Add a warning when negative values are clamped, track the
magnitude of the clamped mass as a diagnostic, and emit a warning when
falling back to the uniform distribution.

---

## 8. Transport Kernel Not Validated as Column-Stochastic

**Severity:** Medium · **Category:** Logic / Theory
**File:** `cwt-sim/cwt/layers/q_update.py:53`

`q_step` documents that `K` must be a "column-stochastic transport kernel" but
only checks `sp.isspmatrix_csr(K)`.  It never verifies that columns sum to
1.0.  If `build_transport_kernel` returns a non-stochastic matrix (possible
with extreme parameter values), the Q-layer update silently violates
probability conservation, producing drift masked by `normalize_prob`.

**Proposed fix:** Add a debug-mode assertion that checks column sums are
within tolerance of 1.0, or validate within `build_transport_kernel`.

---

## 9. `_compute_area_from_deltas` Produces Wrong Area Elements

**Severity:** High · **Category:** Theory
**File:** `cwt-sim/cwt/orchestrator/param_path.py:260–267`

The oriented area element for a 2D path should be the cross product of the
tangent vectors.  But the implementation computes
`delta.get(axis_i) * delta.get(axis_j)` — the product of the two axis
increments *at the same step*.  For a Lissajous or torus path where both axes
change simultaneously, this is not the swept area; it is a diagonal product.
The correct computation is the shoelace/cross-product formula applied to
consecutive tangent vectors.

**Proposed fix:** Compute the area via the shoelace formula:
`0.5 * (λ_i[s]*Δλ_j[s] - λ_j[s]*Δλ_i[s])` summed around the loop, or use
the cross-product of consecutive delta vectors.

---

## 10. `edge_currents` Sign Convention Undocumented and Potentially Inverted

**Severity:** Medium · **Category:** Logic
**File:** `cwt-sim/cwt/layers/readouts.py:370–384`

For a COO representation of `W[row, col]`, an edge from source `u` to
destination `v` is stored with `col = node_index[u]` and
`row = node_index[v]`.  The current `J` is accumulated into `outgoing[cols]`
and `incoming[rows]`, returning `outgoing - incoming`.  The docstring says
"sum_n J_nm − J_mn for every node m" which is ambiguous.  Downstream consumers
(like `memory_current_coupled`) may assume the opposite sign convention,
leading to a global sign flip in the memory term.

**Proposed fix:** Add a unit test that verifies the sign on a simple 2-node
graph with known phases and probability, and document the sign convention
explicitly.

---

## 11. `AppConfig` vs `RunConfig` Schema Disconnect

**Severity:** Medium · **Category:** Structure
**Files:** `cwt-sim/cwt/io/config.py`, `cwt-sim/cwt/orchestrator/scheduler.py:39–59`

The Pydantic `AppConfig` and the dataclass `RunConfig` define overlapping but
inconsistent parameter spaces.  There is no automated bridge from `AppConfig`
to `RunConfig`, so every CLI script must manually unpack config fields,
duplicating the mapping logic and risking drift.  Field names also differ
(`NoiseConfig.phase_std` vs. the scheduler's `theta_sigma` alias).

**Proposed fix:** Generate `RunConfig` from `AppConfig` via a factory method,
or unify the two schemas.  Add a validation test that checks all `AppConfig`
fields have a corresponding `RunConfig` counterpart.

---

## 12. `triage_score` Weights Are Fragile Magic Numbers

**Severity:** Low · **Category:** Structure
**File:** `cwt-sim/cwt/metrics/triage.py:93–100`

The hardcoded weights `0.25 + 0.15 + 0.2 + 0.1 + 0.1 + 0.2 = 1.0` are
embedded as magic numbers.  If anyone adds a new term or adjusts a weight
without rebalancing, the sum will silently deviate from 1.0, making the score
no longer bounded in [0, 1].

**Proposed fix:** Define the weights as named constants, add a static
assertion that they sum to 1.0, and/or normalise the weighted sum at the end.

---

## 13. `phase_factor` Sampling Mode Produces Trivially Zero Curvature

**Severity:** High · **Category:** Theory
**File:** `cwt-sim/cwt/orchestrator/scheduler.py:366–399`

The phase-factor sampler generates neighbour states as
`Psi_i = Psi0 * exp(i * direction * delta)`, where `direction` is a
deterministic real vector.  The curvature of states obtained by pointwise
phase rotation of a fixed state is *identically zero* — multiplying by
`exp(i*f(n))` is a gauge transformation, and Berry curvature is
gauge-invariant.  This means the `phase_factor` sampling mode silently
produces meaningless geometry estimates.

**Proposed fix:** Remove or deprecate the `phase_factor` sample mode.  If a
fast approximation is needed, document clearly that it produces zero curvature
by construction and is only useful for metric estimation.

---

## 14. Rectangle Path Concentrates Entire Area Into 4 Corner Samples

**Severity:** Medium · **Category:** Logic
**File:** `cwt-sim/cwt/orchestrator/param_path.py:151–154`

At rectangle corners (`step_in_edge == 0`), the area is set to
`orientation_sign * corner_area` where `corner_area = |extent_i| * |extent_j|`
(the *total* rectangle area).  On non-corner steps, the area is
`delta[axis_i] * delta[axis_j]`.  For straight edges of the rectangle one
delta component is zero, making the non-corner area identically zero.  The
entire loop area is concentrated into exactly 4 samples (the corners).

**Proposed fix:** Distribute the area evenly across all steps of each edge,
or compute the area via the shoelace sum across all steps.

---

## 15. Global Mutable State in Baseline Axis Map Cache

**Severity:** Low · **Category:** Structure
**File:** `cwt-sim/baselines/common.py:27–35`

`_AXIS_MAP_CACHE` is a module-level global that is lazily populated and never
invalidated.  This is thread-unsafe and will serve stale data in test suites
that modify axis map files between tests.

**Proposed fix:** Replace the global cache with `functools.lru_cache`, or pass
the axis map explicitly through the call chain.

---

## 16. `micro_plaquettes` Generates Quadratic Waste

**Severity:** Low · **Category:** Logic
**File:** `cwt-sim/cwt/geometry/adapt_mesh.py:27–50, 106–108`

`micro_plaquettes` is called fresh for each level with the full level count,
generating a schedule that grows as O(levels²).  But `curvature_anytime` only
uses 4 items per level.  The rest are computed but never consumed.

**Proposed fix:** Generate only the 4 items needed for the current level, or
restructure `micro_plaquettes` as a generator.

---

## 17. `_resolve_tau_scale` Multiplies Absolute and Relative Tau

**Severity:** Medium · **Category:** Logic
**File:** `cwt-sim/cwt/orchestrator/scheduler.py:229–231`

When both `tau` (absolute) and `tau_scale` (relative) are present and not
close to each other, the function returns `tau_abs * tau_rel`.  There is no
physical justification for *multiplying* an absolute delay by a relative
scale — the semantics are ambiguous and the multiplication is likely wrong.

**Proposed fix:** Pick one semantic: either `tau` is the absolute delay and
`tau_scale` is ignored when `tau` is present, or `tau_scale` multiplies the
graph's intrinsic delays and `tau` overrides.  Document the convention and
raise a warning when both are specified with different values.
