# Benchmark D continuous Lindblad response proof report

- Analytic disposition: **PASS_INTERNAL_ANALYTIC**
- Evidence status: **NO_EMPIRICAL_EVIDENCE**
- Scope: internal authored five-state continuous Lindblad generator/readout only.
- No empirical, physical-time, universal-CGT, or derived-CWT-continuum claim is made.
- The proof and assumptions are in `../MODEL_CONTRACT.md`; interval numerics implement it.

## Frozen specialization

- Benchmark/branch: `benchmark_d` / `D0`; controls `b,d`
- Box: `b∈[.01,.05]`, `d∈[.205,.245]`; center `(.03,.225)`
- Core bindings: `lindblad_rhs`, `lindblad_superoperator`, named `mean_position` readout
- Exact affine flow: `x_dot=[(1/5)(K^T-I)-(1/25)I]x+(1/125)1`
- Actual dephasing `.30`; coherent and site-potential scales exactly zero
- Loop: CCW circle `s=.01`, exact reverse CW, equilibrium initialization, continuous model-time integral
- Slow clock: `u=t/T`, `lambda_+(t)=gamma_+(u)`, and `lambda_-(t)=lambda_+(T-t)=gamma_+(1-u)` for `0<=t<=T`
- Units: rates are inverse model-time, `T` is model-time, the readout is a dimensionless
  mean-position index, and `Q` is mean-position-index times model-time.
- Physical interpretation requires external clock and readout calibration, which is absent here.
- Euler stepping and PSD projection are forbidden on the theorem path

## Exact response and analytic dynamic certificate

- `F_bd`: `-28888766872100000000000/235345963257301712101`
- `F_bd` decimal: `-122.750211952929`
- Uniform fixed-state eigenvalue floor: `4/69`
- Primary scale: `1/100`
- `C(s)`: `2873.14398076308` readout·model-time²
- Certified `L_min(s)`: `0.0125795720196663` readout·model-time
- `T0=2^ceil(log2(4C/L_min))`: `1048576`
- Acceptance uses exact-rational directed intervals and `|Qanti-L|<=C/T`; no trajectory
  or fitted slope determines PASS.

## C1-C13

- `C1`: **D0_CORE_BINDING_PASS**
- `C2`: **AFFINE_LINDBLAD_IDENTITY_PASS**
- `C3`: **UNIFORM_CONTRACTION_AND_INVERSE_PASS**
- `C4`: **TRUE_STATIONARY_BRANCH_PASS**
- `C5`: **EXACT_RESPONSE_CURVATURE_PASS**
- `C6`: **ORIENTATION_AND_FACTOR_TWO_PASS**
- `C7`: **IDENTITY_READOUT_NULL_PASS**
- `C8`: **READOUT_COVARIANCE_PASS**
- `C9`: **INVALID_MODEL_VARIANTS_REFUSED**
- `C10`: **AFFINE_SOURCE_REQUIRED_PASS**
- `C11`: **BENCHMARK_C_TRUE_STATIONARY_NULL_PASS**
- `C12`: **RIGOROUS_DYNAMIC_SIGN_CERTIFICATE_PASS**
- `C13`: **ZERO_OMEGA_NONZERO_RESPONSE_NO_GO_PASS**

## Gates

- **PASS** `explicit_contract` — all reviewed model, clock, path, readout, and scope fields equal the frozen contract
- **PASS** `d0_core_kernel_and_readout` — explicit D0 K, named mean_position operator, every config field, and inactive clips match core
- **PASS** `affine_population_generator` — the exact diagonal model is A=(1/5)(K^T-I)-(1/25)I with source (1/125)1
- **PASS** `diagonal_invariant_subspace_core_equivalence` — core RHS/superoperator agree on the complete diagonal invariant subspace at four corners and center
- **PASS** `trace_norm_contraction` — uniform traceless-Hermitian trace-norm propagator bound has M=1 and tau=25
- **PASS** `frozen_inverse_bound` — the branch inverse is uniformly bounded by K_J<=25 in the declared norm
- **PASS** `exact_stationary_branch` — the exact affine linear solve is normalized and stationary without Euler projection
- **PASS** `uniform_full_rank_floor` — every fixed population component is at least the analytic floor 4/69 on the box
- **PASS** `exact_center_oracle` — the center stationary solve, one-form, derivatives, and F_bd reproduce the formal fraction
- **PASS** `nonzero_response_curvature` — F_bd is finite, nonzero, and negative in the frozen orientation
- **PASS** `circle_orientation_reversal` — CW is the exact reverse, no endpoint is duplicated, and exact circle extrema have 1/100 box margins
- **PASS** `qanti_and_did_factor_two` — orientation-odd Qanti uses the half difference and ordinary DID equals 2 Qanti
- **PASS** `identity_readout_null` — the identity readout has exactly zero response curvature
- **PASS** `linear_readout_covariance` — sign reversal and scaling of the readout scale F_bd exactly
- **PASS** `zero_depolarization_refused` — zero depolarization cannot receive the contraction certificate
- **PASS** `coherent_or_gauge_variant_refused` — nonzero coherent or site-potential variants are outside this specialization
- **PASS** `euler_projection_backend_refused` — Euler plus PSD projection is forbidden on the theorem path
- **PASS** `clock_reversal_initialization_mutations_refused` — wrong timing, reversal, and initialization contracts fail closed
- **PASS** `affine_source_omission_refused` — the depolarizing affine source is nonzero and may not be omitted
- **PASS** `benchmark_c_unital_stationary_null` — Benchmark C has true stationary I/3 and zero response under this specialization
- **PASS** `uniform_affine_slow_drive_clock` — the C(s)/T proof uses the frozen affine u=t/T clock and its exact reverse
- **PASS** `rigorous_curvature_and_line_interval` — directed exact-rational intervals certify negative curvature and CCW line integral
- **PASS** `analytic_remainder_certificate` — the C(s)/T bound and reviewed power-of-two T0 rule certify sign before any trajectory
- **PASS** `fixed_and_joint_ladders_certified` — fixed-scale T and joint s/T ladders are certified with every relative bound at most half its predecessor
- **PASS** `smooth_positive_real_projective_state` — the explicit positive-real normalized D0 state map is smooth on the frozen box
- **PASS** `omega_zero_response_nonzero` — Omega_bd=0 exactly while the separately computed response F_bd is nonzero

## Phase 11 supersession boundary

The tracked Phase 11 entry script points to a stale `04_code/src` layout and stale
module path. Its current implementation and tracked summary use finite Euler steps, PSD
projection, cached finite-step branch densities, and mean/final-sample responses. They do
not instantiate this theorem. This package supersedes only the narrow Benchmark-D analytic
question under the explicit contract; it does not validate the Phase 11 global fits.

## Projective no-go control

The auxiliary smooth positive-real D0 map has exact `Omega_bd=0`, while the
separately computed response has nonzero `F_bd`. It is channel-equivalent because
`p` and `theta` are inactive under zero coherent/site terms, but it is not the current
core helper `BranchState` geometry. This refutes only a universal
contraction-implies-alignment inference; it is not substrate evidence.

## Claim ceiling

internal authored Benchmark D five-state Lindblad generator and mean-position readout only; not a derived CWT continuum limit, CGT alignment law, physical model, or empirical evidence
