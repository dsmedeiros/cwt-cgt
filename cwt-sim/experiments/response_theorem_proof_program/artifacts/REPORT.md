# Contractive response theorem proof-program report

- Analytic disposition: **PASS_INTERNAL_ANALYTIC**
- Evidence status: **NO_EMPIRICAL_EVIDENCE**
- This is a finite-dimensional proof plus deterministic authored fixtures.
- It is not a study PASS, empirical evidence, external validation, or a proof of CWT/CGT alignment.
- Numerical checks exercise the implementation; the analytic proof is in `../THEOREM.md`.

## Main result

For a smooth centered update-then-sample response on a uniformly contractive fixed branch,
`Q_c = integral B_c + O(1/N)` with `B_i=-H(I-M)^-1 M X_i`. The on/zero interaction
uses `B^D=B_on-B_0`, its orientation half-difference is `D`, and ordinary DID is `2D`.
Equilibrium-reset scaled loops have the generic bound `C1*s/N+C2*s^2/N`; the stronger
periodic/endpoint-flat bound `C1*s^2/N+C2*s/N^2` requires its separately stated
cancellation assumptions.
The stable-ODE corollary additionally requires a uniformly bounded frozen-branch
inverse and a uniform branch-linearized driven propagator bound. It defines
`Q=integral_0^T r dt`, freezes equilibrium versus periodic/matched initialization,
and uses exact time reversal with one endpoint convention. Propagator decay alone
does not justify `J^-1`; the scalar singular-J counterexample is an executable gate.

## Exact no-go result

The linear contraction `x_n=rho*x_(n-1)+(1-rho)*lambda_n` with the declared centered
readout realizes any smooth response one-form `B=beta`, independently of a normalized
projective state map. Therefore contraction and smoothness do not imply `F_R^D=kappa*Omega`.
Neither `Omega != 0 => response` nor `response => Omega` is valid without extra structure.

## Deterministic metrics

- Generic fixed-loop slope: `-1.06404294526`
- Periodic fixture slope: `-1.99848581905`
- Maximum generic scaled-bound ratio: `3.0466087114`
- Maximum periodic scaled-bound ratio: `1.27647114006`
- Nonzero-baseline interaction relative error: `4.99407511119e-05`
- Exact realizability identity error: `1.11022302463e-16`
- Continuous equilibrium/periodic slopes: `-1.15707529343` / `-1.98285148743`

## Frozen cases

- `C1`: **COUNTEREXAMPLE**
- `C2`: **COUNTEREXAMPLE**
- `C3`: **COUNTEREXAMPLE**
- `C4`: **COUNTEREXAMPLE**
- `C5`: **INELIGIBLE_TAUTOLOGY**
- `C6`: **COUNTEREXAMPLE**
- `C7`: **PASS_LOCAL_INTERNAL**
- `C8`: **OUT_OF_SCOPE**
- `P1`: **PASS_LOCAL_INTERNAL**

C8 is this program's `proof_program_similarity_family_v1` three-dimensional
similarity construction. It is not the adversarial review's separate projector
example; only the qualitative non-Hermitian scope warning is shared. The computed
`-2+2i` value belongs only to this program's fixture.

## Gates

- **PASS** `generic_fixed_loop_inverse_N` — equilibrium-reset fixed-loop remainder log slope lies in [-1.2,-0.8]
- **PASS** `periodic_fixed_loop_improvement` — unique-periodic fixed-loop remainder exhibits the fixture's O(N^-2) cancellation
- **PASS** `scaled_generic_bound` — error/(s/N+s^2/N) <= 4 on the frozen ladder
- **PASS** `scaled_periodic_bound` — error/(s^2/N+s/N^2) <= 2 on the frozen ladder
- **PASS** `area_relative_regime_separation` — at fixed Ns the generic error stalls while the periodic relative error decays
- **PASS** `interaction_with_nonzero_B0_and_factor_two` — D approaches integral(B_on-B_0), B_0 is nonzero, and ordinary DID=2D
- **PASS** `exact_realizability_no_go` — -H(I-M)^-1 M X reproduces an arbitrary declared beta to machine precision
- **PASS** `non_implication_counterexamples` — Omega!=0 does not imply response curvature, and response curvature does not imply Omega
- **PASS** `frozen_case_dispositions` — complete C1-C8/P1 disposition mapping equals {'C1': 'COUNTEREXAMPLE', 'C2': 'COUNTEREXAMPLE', 'C3': 'COUNTEREXAMPLE', 'C4': 'COUNTEREXAMPLE', 'C5': 'INELIGIBLE_TAUTOLOGY', 'C6': 'COUNTEREXAMPLE', 'C7': 'PASS_LOCAL_INTERNAL', 'C8': 'OUT_OF_SCOPE', 'P1': 'PASS_LOCAL_INTERNAL'}
- **PASS** `computed_counterexample_constructions` — C3-C6 are computed forms/dynamics, not declarative dispositions
- **PASS** `gauge_and_coordinate_covariance` — gauge and coordinate covariance errors <= 1e-7
- **PASS** `three_dimensional_aligned_oracle_control` — deliberately aligned oracle/positive implementation control has F_R=2*Omega on full-rank and held-out directions
- **PASS** `nonnormal_scope_boundary` — fixed-gap non-normal case is explicitly out of the right-state theorem scope
- **PASS** `continuous_stable_ode_rates` — stable-ODE fixture exhibits generic O(tau/T) and stronger periodic cancellation
- **PASS** `continuous_inverse_assumption_is_independent` — driven propagator decay does not imply the separately required bounded frozen inverse
- **PASS** `continuous_discrete_alpha_mapping` — alpha(dt)=1-exp(-dt/tau) exactly matches the held-input relaxation map
- **PASS** `alignment_characterization_and_bound` — zero-set/collinearity/closure conditions and the comass center-kappa approximation bound are explicit

## Claim ceiling

The program proves only the declared contractive-class response reduction and the exact
realizability/no-go statement. P1 is a deliberately aligned oracle/positive implementation
control, not an independently measured response; C5 is a 2D
tautology, and C8 is outside the pure-state scope. The repository still has no qualifying
external active-loop substrate or empirical evidence for a CGT/readout alignment law.
