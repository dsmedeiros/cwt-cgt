# Benchmark D true-fixed open-response proof report

- Analytic disposition: **PASS_INTERNAL_ANALYTIC**
- Evidence status: **NO_EMPIRICAL_EVIDENCE**
- Scope: internal synthetic authored five-state fixed-tick channel/readout only.
- This is not empirical evidence, physical time, the full scheduler, or CGT alignment.
- Numerical gates exercise the implementation; the proof is in `../MODEL_CONTRACT.md`.

## Frozen specialization

- Core map: `cwt.cgt.open_system.apply_local_open_step`
- Benchmark/branch: `benchmark_d` / fixed `D0` (no continuation)
- Controls: `b in [0.01,0.05]`, `d in [0.205,0.245]`; center `(0.03,0.225)`
- Readout: centered geometry-blind `mean_position=diag(1,2,3,4,5)`
- Channel: `dt=.18`, edge jump `.20`, depolarizing `.008=1/125`, dephasing `.30`,
  coherent/site-potential scales zero
- Cycle: right-endpoint update then sample; CW is the exact stored-sequence reverse

The diagonal invariant subspace obeys `x' = Mx+c`, with
`M=(124/125)[(1-9/250)I+(9/250)K]^T` and `c=(1/625)1`.
The true fixed branch is solved as `[I-M]^-1 c`.

## Exact result

- `F_bd` fraction: `-1389405980846240823998759336989273383099794763750000000000/2559023550169319630994375590863181495045970285707766901`
- `F_bd` decimal: `-542.943803996767`
- Independent analytic float: `-542.943803996753`
- Central-difference curl: `-542.943806013518`
- Fixed-loop tail log slope: `-1.00175018655`
- Shrinking-loop finest area-density relative error: `0.0560710298037`
- Exact global full-rank eigenvalue floor from depolarization: `0.0016`
- Sampled minimum fixed eigenvalue on the 5x5 diagnostic mesh: `0.151529111263`
- Sampled fixed-branch variation on that mesh: `0.0659322174751`
- Maximum fixed-solver centering budget / observed density error: `0.000119499682372`

The shrinking ladder doubles `N*s`; holding `N*s` fixed is not accepted because the
generic equilibrium-reset remainder is `O(s/N)`. Its 0.60 ratio and 0.10 final-error
thresholds were selected during internal harness development, after the ladder design;
they are deterministic regression checks, not preregistered evidence.

## Frozen case dispositions

- `C1`: **CORE_DIAGONAL_EQUIVALENCE_PASS**
- `C2`: **EXACT_CONTRACTION_CERTIFIED**
- `C3`: **NONZERO_RESPONSE_CURVATURE_PASS**
- `C4`: **FIXED_LOOP_ASYMPTOTIC_PASS**
- `C5`: **SHRINKING_LOOP_LIMIT_PASS**
- `C6`: **IDENTITY_READOUT_ZERO_PASS**
- `C7`: **CONSTANT_BRANCH_ZERO_PASS**
- `C8`: **DEPOLARIZING_ZERO_REFUSES_CERTIFICATE**
- `C9`: **BENCHMARK_C_UNITAL_ZERO_PASS**
- `C10`: **PHASE10_BENCHMARK_C_TWO_STEP_SURROGATE_NOT_FIXED**

## Gates

- **PASS** `named_core_binding` — D0 analytic kernel and diagonal affine trace agree with core APIs
- **PASS** `named_core_readout_binding` — executed response path obtains core mean_position=diag(1,2,3,4,5)
- **PASS** `exact_kraus_and_margin_certificate` — clip/support/rescale/square-root margins are strictly positive and TP is exact
- **PASS** `global_contraction_certificate` — global trace/L1 factor is exactly 124/125
- **PASS** `true_full_rank_fixed_branch` — exact depolarizing floor gives full rank; sampled branch varies and residual is certified
- **PASS** `exact_fraction_oracle` — Fraction-valued differentiation reproduces the independent formal F_bd fraction
- **PASS** `nonzero_response_curvature` — analytic and independent numerical curls match the exact negative nonzero F_bd
- **PASS** `constant_projective_reference_zero` — separate channel-equivalent constant normalized state has exact Omega_bd=0
- **PASS** `fixed_loop_one_over_n` — Q_anti approaches the finite-loop line integral with O(1/N) endpoint error
- **PASS** `registered_loop_domain_containment` — every registered loop point is inside the certified closed D0 control box
- **PASS** `shrinking_loop_area_limit` — development-selected in-box regression: growing N*s drives Q_anti/s^2 toward F_bd
- **PASS** `fixed_solver_centering_budget` — conservative fixed-solver centering budget is negligible versus observed convergence error
- **PASS** `loop_update_reversal_endpoint_contract` — CW is stored-sequence reverse; initial duplicate skipped; close updated once
- **PASS** `identity_readout_null` — identity readout has zero orientation-odd response
- **PASS** `constant_branch_null` — constant fixed branch has zero orientation-odd response
- **PASS** `depolarizing_zero_refusal` — depolarizing=0 cannot receive the strict 124/125 contraction certificate
- **PASS** `benchmark_c_true_fixed_unital_null` — Benchmark C C0 has true fixed I/3 and zero centered primary response
- **PASS** `phase10_benchmark_c_two_step_surrogate_rejected` — tracked Phase10 Benchmark-C branch_steps=2 surrogate is demonstrably not fixed

## Historical surrogate limitation

The historical entry script explicitly set `branch_steps=2`; the tracked Phase10
Benchmark-C JSON records that value and recommended `gamma=0.2`. The current library
default is 3, while `cwt/cgt/analysis/phase10_analysis.py` is the current recomputation
implementation. Recomputing C0 from the explicit tracked configuration gives a
nonzero fixed residual, so it is a finite-step surrogate rather than a stationary
density. A separate Benchmark-D three-step diagnostic is reported only as a distinct
limitation check and does not validate the tracked Benchmark-C artifact.

## Projective reference control

The authored stationary-probability D0 geometry is not used as a smooth projective
branch. Instead the frozen zero coherent/site terms make a separately declared
constant normalized reference `p_j=1/5, theta_j=0` channel-equivalent. Its derivatives
and `Omega_bd` are exactly zero. Together with nonzero response curvature this is only
a constant-reference no-go control; it supplies no CGT alignment evidence.

## Claim ceiling

Internal synthetic authored five-state fixed-tick Benchmark D D0 channel/readout only; not the full scheduler, physical time, CGT alignment, empirical evidence, external validation, topology, or a universal response law.
The exact-zero constant reference and nonzero response instantiate only the statement
that response curvature does not by itself imply a universal CGT alignment law.
