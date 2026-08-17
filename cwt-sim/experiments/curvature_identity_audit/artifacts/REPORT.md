# CGT/response curvature identity audit

- Analytic disposition: **PASS_INTERNAL_ANALYTIC**
- Evidence status: **NO_EMPIRICAL_EVIDENCE**
- Scope: three internal authored analytic cases; no empirical or physical evidence.
- Exact proofs own acceptance; numerical spectral/finite-difference/Wilson checks are regressions only.

## Common-origin result

- `B_R=sigma^*beta_R`; on a local Berry gauge, `A_Lambda=sigma^*P^*a_B`.
- `kappa` is a smooth real scalar on `Lambda`.
- Exact branch condition: `sigma^*(d beta_R)-kappa sigma^*(P^*omega_FS)=0`.
- The condition is necessary and sufficient only on branch tangents; ambient equality is not required.
- For constant kappa, `d(B_R-kappa A_Lambda)=0`; only on a contractible chart is `B_R-kappa A_Lambda=dchi`.
- Noncontractible periods are periods of the pulled-back form; Chern obstructions remain.
- A pointwise 2D quotient is tautological, not a prediction.

## QP-1 calibration

- Classification: `SAME_CURVATURE_CALIBRATION_ONLY`.
- `A_x=2*pi*sin(pi*y/2)^2`, `A_y=0`, `Omega_xy=-pi^2*sin(pi*y)`.
- `O_i=+partial_i H` gives `+Omega`; `O_i=-partial_i H` gives `-Omega`.
- Full antisymmetrization is exactly twice the half convention.
- Chern number: `-1`; no global smooth connection.
- This is not a finite-speed or live-CWT response result.

## Benchmark C same-primitives separation

- Classification: `SAME_PRIMITIVE_MANIFOLD_DIFFERENT_CONNECTIONS_DERIVED_MIXED_HESSIAN`.
- `Omega_uv(0,0)=7/48`.
- `F_uv(0,0)=-222183/2800000`.
- Exactly `d beta_R=-m dJ_x wedge dtheta` with `dJ_x=J_xp dp+J_xx dtheta+J_xK dK`.
- `d^2theta` and symmetric `J_xx` cancel; mixed `J_xp` and `J_xK` terms remain.
- Exact quotient gradient: `54539433/43750000, 11560887/21875000`; the relation is not constant.
- Gain zero and alpha one null the response while leaving projective curvature nonzero.
- The theorem statistic is the fixed-tick cycle sum, not the legacy sample mean.

## Benchmark D zero-set obstruction

- Classification: `SAME_MODEL_ZERO_SET_OBSTRUCTION`.
- The exact affine stationary branch `xbar=-A^-1c` supplies `psi_j=sqrt(xbar_j)` with no floor.
- Projective curvature: `0/1`.
- Response curvature: `-28888766872100000000000/235345963257301712101`.
- Identical A,c,O provenance plus `Omega=0,F!=0` rules out finite scalar `F=kappa Omega` and frozen zero-preserving homogeneous linear tensor maps here.
- Arbitrary nonlinear or affine Omega-only maps are not ruled out by this zero-set argument.
- The separate commuting diagonal mixed-density Uhlmann-null statement is not the projective proof.

## Cases

- `T0`: **COMMON_ORIGIN_PULLBACK_THEOREM_PASS**
- `QP1`: **SAME_CURVATURE_CALIBRATION_ONLY**
- `BC`: **SAME_PRIMITIVE_MANIFOLD_DIFFERENT_CONNECTIONS_DERIVED_MIXED_HESSIAN**
- `BD`: **SAME_MODEL_ZERO_SET_OBSTRUCTION**
- `FUTURE`: **ALIGNMENT_TEST_REQUIREMENTS_FROZEN_NO_CURRENT_PASS**
- `SCOPE`: **PASS_INTERNAL_ANALYTIC_NO_EMPIRICAL_EVIDENCE**

## Gates

- **PASS** `common_origin_branch_tangent_equivalence` — alignment is exactly equality of the pulled-back two-forms on every branch tangent pair
- **PASS** `local_exact_potential_scope` — the local exact-potential statement is restricted to constant kappa on a contractible gauge patch
- **PASS** `global_period_and_chern_obstructions` — noncontractible periods and nonzero Chern flux are explicit global obstructions
- **PASS** `alignment_refusal_matrix` — pointwise fitting, 2D quotient tautology, unfrozen maps, auxiliary states, and ontology upgrades are refused
- **PASS** `qp1_same_operator_projector` — the state projector and Kubo perturbations derive from the same Hermitian QP-1 operator
- **PASS** `qp1_exact_connection_curvature_gap` — A, Omega, and the positive spectral gap are analytic on the declared chart
- **PASS** `qp1_kubo_sign_and_antisymmetrization` — +dH gives +Omega, -dH gives -Omega, and full antisymmetrization is twice the half convention
- **PASS** `qp1_patch_transition_and_chern` — the north/south transition yields Chern number -1 and forbids a global smooth connection
- **PASS** `qp1_spectral_regression_only` — numerical eigensystem evaluation cross-checks but does not establish the exact identity
- **PASS** `benchmark_c_core_branch_binding` — the analytic p, theta, and K formulas equal the core Benchmark-C C0 branch on the frozen patch
- **PASS** `benchmark_c_exact_berry_pullback` — A=sum p dtheta and Omega=dA reproduce the exact 7/48 center value
- **PASS** `benchmark_c_exact_response_pullback` — beta=-(1-alpha)/alpha H.dtheta and F=d beta reproduce the exact center response jet
- **PASS** `benchmark_c_exact_response_decomposition` — d beta_R=-m dJ_x wedge dtheta with dJ_x=J_xp dp+J_xx dtheta+J_xK dK; d2theta and symmetric J_xx cancel while mixed J_xp/J_xK remain
- **PASS** `benchmark_c_center_oracle_and_nonconstant_quotient` — the exact quotient has the reviewed center value and nonzero exact gradient, so it is not constant
- **PASS** `benchmark_c_gain_and_relaxation_nulls` — gain=0 and alpha=1 null response while Omega persists, and response scales exactly with gain
- **PASS** `benchmark_c_numerical_regressions_only` — finite differences and Wilson flux cross-check the analytic proof without supplying it
- **PASS** `benchmark_c_cycle_sum_scope` — the theorem uses a fixed-tick cycle sum; the legacy sample mean is not promoted to the same response
- **PASS** `benchmark_d_shared_model_provenance` — geometry and response use the identical exact A, c, and named mean-position O identity
- **PASS** `benchmark_d_exact_stationary_positive_no_floor` — xbar=-A^-1c is exact, normalized, uniformly positive, and encoded without floor/clip/repair
- **PASS** `benchmark_d_real_projective_lift_zero_curvature` — the actual smooth positive stationary lift is real and normalized, hence A=Omega=0 exactly
- **PASS** `benchmark_d_exact_nonzero_response` — the identical exact A,c,O model has the formal nonzero response curvature
- **PASS** `benchmark_d_zero_set_obstruction` — Omega=0 with F!=0 rules out a finite scalar F=kappa*Omega and every frozen zero-preserving homogeneous linear tensor map for this encoding/readout
- **PASS** `benchmark_d_mixed_state_scope` — the diagonal mixed-state Uhlmann-null statement is separate from the projective proof
- **PASS** `future_alignment_fail_closed` — a future positive CWT alignment test needs >=3 full-rank directions and held-out oblique prediction
- **PASS** `claim_ceiling` — the result is internal analytic only, with no empirical, physical, universal-CWT, or alignment upgrade

## Claim ceiling

internal authored QP-1 calibration and Benchmark-C/Benchmark-D analytic identity audit only; not universal CWT, physical response, empirical evidence, or a general CGT-response alignment law
