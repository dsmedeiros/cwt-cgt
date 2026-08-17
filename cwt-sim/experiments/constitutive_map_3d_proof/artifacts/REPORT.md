# Three-dimensional constitutive-map proof program

- Analytic disposition: **PASS_INTERNAL_ANALYTIC**
- Evidence status: **NO_EMPIRICAL_EVIDENCE**
- Relation scope: **MODEL_SPECIFIC_RELATIONS_ONLY**
- Scope: two internal authored analytic model checks; no empirical or physical evidence.
- Exact derivations own acceptance; numerical checks are regressions only.

## BC3 kinetic-control separation

- Classification: `SAME_MODEL_KINETIC_CONTROL_GEOMETRY_KERNEL_SEPARATION`.
- Controls are `(u,v,alpha)`; gain is fixed and is not a third control.
- `beta=-((1-alpha)/alpha) eta` and `F=alpha^-2 d alpha wedge eta-((1-alpha)/alpha)d eta`.
- Component order is `(F_v_alpha,F_alpha_u,F_uv)`.
- Geometry is alpha-independent rank one, while the response changes across the alpha fiber.
- The heldout oblique area vector `(1,2,2)`, midpoint lines, and center interval are locked before the response oracle runs.
- Prediction lock: `95eb55a19b970c1e6f3a6197b7438a3b89d5df8b9077d301c4c643290a9085e1`.
- Exact-lattice no-libm binary64 intervals conjunctively certify all four formal remainder rows; the last two are locked synthetic holdouts.
- Missing authenticated enclosures are INDETERMINATE and any finite conjunct violation is FAIL.
- The scalar float recurrence is `NON_AUTHORITATIVE_DIAGNOSTIC`: it is never unioned into or used to widen the exact-lattice interval and is not a formal PASS input.
- Its development-selected drift ceiling is `1/1000000` density units; the current maximum interval distance is `1.8187337941233395e-08` and the diagnostic status is `PASS_NONAUTHORITATIVE_REGRESSION`.
- Nonfinite or over-ceiling scalar drift leaves the formal theorem gates unchanged but blocks publication as `BLOCKED_DIAGNOSTIC_DRIFT`.

## QP3 ambient calibration

- Classification: `SAME_OPERATOR_SAME_CONNECTION_FULL_RANK_CALIBRATION_ONLY`.
- `P+=(I+n.sigma)/2`, `H=3/5 I+2/5 P+`, gap `2/5` on a contractible tube away from zero.
- `Omega_ij=epsilon_ijk lambda_k/(2|lambda|^3)`.
- Independent spectral Kubo `O_i=+partial_i H` gives `+Omega`; conventional `-partial_i H` gives `-Omega`.
- Full antisymmetrization is exactly twice the half convention.
- Centers `e1,e2,e3` span rank three; heldout `(1,2,2)/3` has density exactly `1/2`.
- Exact Pauli/projector and north/south patch algebra own acceptance; numerical spectral rows are regressions only.
- This is a calibration-only same-operator identity, not finite-speed CWT response.

## Claim ceiling

internal synthetic Benchmark-C kinetic-control derivation and experiment-local QP3 same-operator calibration only; not universal or full CWT, physical response, empirical evidence, or a general CGT-response alignment law

No universal, full-CWT, physical, empirical, or general alignment claim is made.

## Cases

- `BC3`: **SAME_MODEL_KINETIC_CONTROL_GEOMETRY_KERNEL_SEPARATION**
- `QP3`: **SAME_OPERATOR_SAME_CONNECTION_FULL_RANK_CALIBRATION_ONLY**
- `REFUSALS`: **INELIGIBLE_AND_CIRCULAR_CONTROLS_REFUSED**
- `SCOPE`: **PASS_INTERNAL_ANALYTIC_NO_EMPIRICAL_EVIDENCE_MODEL_SPECIFIC_ONLY**

## Gates

- **PASS** `bc3_contract_and_domain` — the frozen 3D domain, heldout tangents, area vector, and exact contract must match
- **PASS** `bc3_local_c0_and_predecessor_binding` — the theorem must use the source-bound experiment-local exact C0 formulas; full-box clip/wrap margins are analytic and core samples are regression-only
- **PASS** `bc3_dynamics_contraction_and_conventions` — variable-alpha dynamics must have rho<=7/10, equilibrium init, right-endpoint sampling, and exact reverse
- **PASS** `bc3_exact_factorization_and_covariance` — F must be the frozen exterior derivative factorization with closure, covariance, and no response fit
- **PASS** `bc3_directed_interval_nonzero_margins` — directed rational interval enclosures must prove every heldout response component and density nonzero
- **PASS** `bc3_geometry_rank1_and_alpha_fiber_separation` — Omega must be alpha-independent rank-one while response changes across the alpha fiber
- **PASS** `bc3_prediction_lock_and_heldout_split` — the immutable prediction and distinct heldout center must pass the exact INIT->PREDICTION_LOCKED->ORACLE_RUN->VERIFIED sequence
- **PASS** `bc3_response_oracle_firewall` — the response oracle must receive no geometry, prediction, area, orientation label, outcome, or heldout fit
- **PASS** `bc3_generic_ladder_and_nulls` — the generic O(s/N) ladder must stay in-domain with sN increasing and exact scoped nulls/factor two
- **PASS** `qp3_same_operator_projector_and_gap` — experiment-local P+, H, eigenvalues, gap, and spectral projector must agree without claiming the old 2D builder
- **PASS** `qp3_monopole_geometry` — geometry must independently compute the ambient monopole curvature from the shared projector
- **PASS** `qp3_kubo_sign_and_factor` — +dH must give +Omega, -dH must give -Omega, and full antisymmetrization must equal twice half
- **PASS** `qp3_rank3_centers_and_heldout` — e1,e2,e3 two-form vectors must span rank three and predict heldout h density exactly one half
- **PASS** `qp3_gauge_coordinate_closure_and_chern` — the tensor must be gauge invariant, coordinate covariant, closed off the origin, and retain its Chern obstruction
- **PASS** `qp3_constant_projector_and_nonscalar_refusals` — constant projectors must be null and the declared nonscalar K must fail closure
- **PASS** `ineligible_and_circular_control_matrix` — every tautological, circular, auxiliary, fitted, and claim-inflating control must be refused
- **PASS** `claim_ceiling_and_evidence_scope` — status, evidence, model-specific ceiling, immutable ownership, and dispositions must match the contract
