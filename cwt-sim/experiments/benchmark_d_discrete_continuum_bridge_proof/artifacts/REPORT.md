# Benchmark D rational discrete/continuous bridge proof

- Analytic disposition: **PASS_INTERNAL_ANALYTIC**
- Evidence status: **NO_EMPIRICAL_EVIDENCE**
- Scope: authored five-state D0 diagonal population sector and named mean-position readout.
- No full-density, scheduler, calibrated physical-time, empirical, CGT-alignment, or general-CWT claim.
- The proof and assumptions are in `../MODEL_CONTRACT.md`; finite ladders do not establish PASS.

## Exact primary family

- Abstract exact-Fraction family: `q_h=(1/25)h`, rational `0<h<=1/5`; `a=1/5`.
- `M_h=(1-delta*h)(I+h*a*(K^T-I))=I+h*A_h`.
- `c_h=h*(delta/5)1`; `A_h=a(1-delta*h)(K^T-I)-delta*I`.
- Exact stationary branch `xbar_h=-A_h^-1*c`; no iterative branch/fixed helper.
- Finite core calls are provenance/regression only on the frozen representable domain `1/10^12<=h<=1/5`; they do not prove uniform runtime equivalence.
- Uniformity comes only from the exact symbolic affine identity, not sampled core calls.

## Exact response bridge

- `h*B_h=B_CT(a_h)+h*d(H*xbar_h)`; the added term is an exact gradient.
- `h*F_h=F_CT(a_h)` exactly on closed loops.
- Center continuous curvature: `-28888766872100000000000/235345963257301712101`.
- First h coefficient: `228322311704703213246688000000/44415389442843585257542657921`.
- Directed derivative enclosure: `5.67917909685923<88`; therefore `|hF_h-F_CT|<88h`.

## Fixed-time integrated response

- Exact rational scale domain `0<s<=1/100`; the registered report uses `s=1/100`.
- At `s=1/100`, exact extrema leave `1/100` to every D0 box face.
- Common affine clock, positive-integer `N=T/h`, right endpoints, one closing endpoint, exact reverse, and exact discrete/continuous equilibria are frozen.
- `S_h=sum H[x_n-xbar_h(lambda_n)]`; `Q_h=h*S_h` has model-time units.
- `|Q_h-Q_CT|<=h[(214/25)T+120*pi*s]` for each orientation and Qanti.
- With `pi<=355/113`, the circle coefficient is exactly `42600/113`.
- The certificate recomputes every fixed-time coefficient/premise; formula strings cannot self-attest PASS.
- Primary order: `h->0` at fixed `T,s`, then `T->infinity`, then optional `s->0` within the declared domain.
- Limit interchangeability is not claimed; the stated joint conditions are only sufficient conditions.

## Prior-artifact boundary

- The discrete `h=9/50,q=1/125` proof is off-family because `(1/25)h=9/1250`.
- The continuous Lindblad proof is a hash-bound target context, not new or empirical evidence.
- Both prior trees are recursively path-bound; nested additions, omissions, path/type substitutions, symlinks, and reparse entries are rejected.
- Neither prior artifact tree is regenerated or used as numerical acceptance data here.

## C1-C12

- `C1`: **PRIMARY_RATIONAL_FAMILY_LOCKED**
- `C2`: **CORE_CPTP_SAFETY_AND_DIAGONAL_IDENTITY_PASS**
- `C3`: **GENERATOR_SOURCE_AND_C2_CONTROL_PASS**
- `C4`: **EXACT_STATIONARY_BRANCH_AND_CONTRACTION_PASS**
- `C5`: **EXACT_hB_GRADIENT_IDENTITY_PASS**
- `C6`: **EXACT_hF_SIGN_LIMIT_AND_ERROR_BOUND_PASS**
- `C7`: **Q_SCALING_CLOCK_REVERSAL_AND_FACTORS_PASS**
- `C8`: **FIXED_TIME_BRIDGE_BOUND_PASS**
- `C9`: **ITERATED_AND_CONDITIONAL_JOINT_LIMIT_SCOPE_PASS**
- `C10`: **LEGACY_CONTEXT_OFF_FAMILY_AND_HASH_BOUND**
- `C11`: **ADVERSARIAL_REFUSAL_MATRIX_COMPLETE**
- `C12`: **CLAIM_CEILING_NO_EVIDENCE_UPGRADE**

## Gates

- **PASS** `contract_exact_primary_family` — the abstract exact-Fraction q_h=delta*h family and every frozen field are unchanged
- **PASS** `d0_clip_inactive` — the complete D0 box is strictly inside every kernel clip boundary
- **PASS** `kraus_cp_tp_uniform` — the frozen Kraus map is CP/TP with exact loss and radicand margins
- **PASS** `safety_rescale_inactive` — the core 0.98 Kraus rescale branch is uniformly inactive
- **PASS** `projection_inactive` — the PSD/trace projection makes no material change on the tested complete population basis
- **PASS** `finite_core_diagonal_regression` — finite core calls regress the diagonal basis/readout but do not prove uniform runtime equivalence
- **PASS** `exact_generator_source_identity` — M_h=I+hA_h and c_h=h(delta/5)1 exactly, with K transpose
- **PASS** `uniform_c2_parameter_control` — uniform exact C2 parameter derivative bounds hold on the rational family
- **PASS** `exact_stationary_branch` — xbar_h=-A_h^-1 c exactly and the analytic population floor is 4/69
- **PASS** `uniform_contraction_and_resolvent` — the population map contracts by 1-delta*h and has the uniform inverse/fixed-branch bounds
- **PASS** `exact_hB_gradient_identity` — hB_h=B_CT(a_h)+h d(H xbar_h) exactly
- **PASS** `closed_loop_gradient_cancellation` — the exact-gradient correction has zero curl and zero closed-loop integral
- **PASS** `exact_hF_identity` — hF_h equals the continuous generator curvature at a_h=a(1-delta*h)
- **PASS** `curvature_sign_interval` — directed exact intervals certify hF_h<0 for the entire h domain
- **PASS** `center_limit_oracle` — the recomputed h->0 fraction and first h coefficient equal the independent formal oracles
- **PASS** `curvature_error_bound` — the mean-value theorem gives the uniform strict bound |hF_h-F_CT|<88h
- **PASS** `response_units_and_h_scaling` — the reducer uses h-scaled centered right-endpoint sums in model-time units
- **PASS** `loop_clock_reversal_endpoint_contract` — right endpoints, one closing endpoint, a common affine clock, and exact reversal are frozen
- **PASS** `qanti_and_did_factors` — Qanti is the half difference and the ordinary orientation difference is exactly 2Qanti
- **PASS** `fixed_time_bridge_bound` — every fixed-T premise is exactly recomputed and the bound uses no fitted trajectory gate
- **PASS** `scale_domain_uniform_containment` — all rational 0<s<=1/100 loops remain in the box with uniform constants
- **PASS** `iterated_and_joint_limit_scope` — only the proved iterated limit and explicitly sufficient joint conditions are claimed
- **PASS** `legacy_context_off_family` — the existing h=9/50,q=1/125 open proof is explicitly off the rational primary family
- **PASS** `context_artifact_hash_closure` — both recursive path-bound prior bundles are exact ordinary-file closures
- **PASS** `refusal_matrix_complete` — every frozen refusal case is represented and fails closed
- **PASS** `claim_ceiling` — the disposition is internal analytic only and makes no empirical/full-density/CGT claim

## Claim ceiling

exact rational bridge on the authored five-state D0 diagonal invariant population sector and mean-position readout in uncalibrated model-time only; no full-density, scheduler, physical, empirical, CGT-alignment, general-CWT, topology, or population claim
