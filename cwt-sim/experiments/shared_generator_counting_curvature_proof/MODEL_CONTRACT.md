# Shared-generator counting-curvature proof contract

## Claim ceiling

This experiment can report only `PASS_INTERNAL_ANALYTIC`,
`NO_EMPIRICAL_EVIDENCE`, and `MODEL_SPECIFIC_RELATIONS_ONLY` for the exact
five-state Benchmark-D D0 specializations below. It does not prove a universal
or full-CWT response/CGT alignment, a calibrated physical response, or empirical
evidence.

The exact zero-state-curvature/nonzero-response controls refute only
`SAME_CURVATURE` and a frozen zero-preserving homogeneous `Omega`-only map for
the declared state geometry. Affine, nonlinear, and generator-dependent maps
remain open.

All theorem acceptance is exact rational or Gaussian-rational algebra. Float
core comparisons and finite differences are provenance/drift regressions only.

## One generator family

Let `K(b,d)` be the unclipped five-state reflecting D0 kernel with
`k_plus=d+b`, `k_minus=d-b`, edge rate `a=1/5`, depolarization `delta`,
dephasing `3/10`, site potential zero, and branch phase zero. On column-stacked
matrices the trace-preserving generator is

`W rho = -i[H,rho] + jump/dephasing dissipators + delta(I Tr(rho)/5-rho)`.

The coherent Hamiltonian is the real nearest-neighbor path Hamiltonian with
entry `h*d`. The exact stationary branch is the unique solution of
`W pi=0`, `Tr pi=1`; no iterative, projected, continuation, or auxiliary branch
is permitted. Geometry, counting, and response all use this same `W`, source,
and `pi`.

Positive counting field `q` counts the directed middle-edge transition from
index 1 to index 2 (physical nodes 2 to 3). Only gain terms are tilted:
`W_q[gain m<-n]=exp(q d_mn) W[gain m<-n]`.

## T0: classical three-control obstruction

Controls are `(b,d,delta)` at center `(3/100,9/40,1/25)`, with `h=0`.
The exact Drazin inverse is

`R=(W+pi 1^T)^-1-pi 1^T`,

and satisfies `WR=RW=I-pi 1^T`, `R pi=0`, and `1^T R=0`. With
`X_i=partial_i pi`, counted-current row `j=1^T partial_q W_q|_0`,

`B_i=j R X_i`, `F_ij=partial_i B_j-partial_j B_i`.

The actual stationary density is diagonal. Its positive-real projective lift
has zero Berry curvature, and the commuting density family has zero Uhlmann
curvature. The exact radial scaling identity
`b X_b+d X_d+delta X_delta=0` makes the metric rank two while counted-current
curvature is nonzero. Classification:

`SAME_GENERATOR_CLASSICAL_THREE_CONTROL_ZERO_SET_OBSTRUCTION`.

Uniformly on `delta in [1/50,3/50]`, the computed short-time norm budget is

`4 h_max d_max + 16 a d_max + 10 gamma_deph`

`=147/1000 + 784/1000 + 3000/1000 = 3931/1000`.

At `t0=1/40`, the exact integral construction gives the full-rank stationary
floor `5991/80000000`, trace-norm contraction rate at least `1/50`, uniqueness,
and Drazin bound `50`.
At the frozen center `delta=1/25`, contraction is `1/25` and the Drazin bound
is `25`. The no-depolarizing-reset factor is derived as
`exp(-delta_max t0) >= 1-delta_max t0 = 1997/2000`, not supplied as a flag.
The norm budget is in the superoperator norm induced by the matrix spectral
operator norm. With `x=C t0=3931/40000<1`, the exponential series gives
`exp(x)-1 <= x/(1-x)`, hence
`||Phi_t(I/5)-I/5||_op <= 3931/180345`. Therefore
`lambda_min(Phi_t(I/5)) >= 32138/180345 > 3/20`; the displayed integral floor
uses the smaller exact `3/20` bound.

## T1: coherent three-control obstruction

Controls range over

- `b in [1/100,1/20]`,
- `d in [41/200,49/200]`,
- `h in [1/20,3/20]`,

at center `(3/100,9/40,1/10)`, with `delta=1/25`.

Writing `W=L0+delta(D-I)`, the separately computed norm terms
`4 h_max d_max + 16 a d_max + 10 gamma_deph`
`=147/1000 + 784/1000 + 3000/1000 = 3931/1000 < 4` and `t0=1/40` give

`pi >= 2997/20000000 I`.

Here contraction is exactly `1/25`, the Drazin bound is `25`, and the derived
no-reset lower factor is `1-(1/25)(1/40)=999/1000`. Positive lower bounds on
every frozen jump/dephasing rate establish the Lindblad/CPTP premise used in
the variation-of-constants floor certificate. The same induced-norm series
bound gives the inner-semigroup floor `32138/180345 > 3/20` without assuming
that CPTP alone implies the floor.

Depolarization gives trace-norm contraction `exp(-t/25)`, uniqueness, and
the Drazin bound 25. The exact tangent Gram determinant and the exact SLD metric
determinant are positive, so the stationary branch and SLD metric have rank
three.

The fixed gauge `U=diag(1,i,-1,-i,1)` makes the stationary density, all three
tangents, and all SLDs real symmetric. Therefore the mean Uhlmann curvature
`OmegaM_ij=(1/(4i))Tr[pi[L_i,L_j]]` is exactly zero, while all three counted
response-curvature components are nonzero. Classification:

`SAME_GENERATOR_COHERENT_THREE_CONTROL_ZERO_SET_OBSTRUCTION`.

## T2: extended FCS eigenbundle identity

Let `l_q^T W_q=theta(q)l_q^T`, `W_q r_q=theta(q)r_q`, with
`l_q^T r_q=1` and `1^T r_q=1`. The FCS connection is
`A_i(q)=l_q^T partial_i r_q`. The geometric cumulant is
`-closed_integral A(q)`, so exact eigenvector differentiation gives

`B_i=-partial_q A_i|_0`,

`F_R=-partial_q d_parameter A|_0`.

The acceptance path constructs the exact first `q` jet of `W_q`, differentiates
the left/right eigenvector equations, and independently takes the parameter
curl of the resulting normal-connection jet. It does not accept literal
`W_q`, current, or curvature flags.

This is a common-connection identity in the normal counting-field jet of the
extended non-trace-preserving eigenbundle. It is distinct from the state CGT
connection. Classification:

`FCS_EXTENDED_EIGENBUNDLE_RESPONSE_IDENTITY_DISTINCT_FROM_STATE_CGT`.

Reversing the count reruns the exact stationary/Drazin response with the
opposite current orientation and independently recomputes both `B` and `F`;
the results are their exact negatives. The exact orientation algebra defines
`Qanti=(Qplus-Qminus)/2`, so the full orientation difference is `2 Qanti`.
Acceptance is limited to this sign/factor algebra and the exact local curvature
at the frozen centers. No finite-time loop, remainder, asymptotic-rate, or
numerical-ladder claim is made.

Generator rates have inverse model-time units. For either control chart,
`B_i` has count per unit of control `i`, and `F_ij` has count per control-area.
Thus `B_delta` and `B_h` have count-times-model-time units, mixed components
with `delta` or `h` do likewise, while the `(b,d)` components have count units.
This is uncalibrated continuous model-time, not physical time.

Geometry receives only a typed stationary/tangent record. Before the response
oracle runs, a typed immutable lock freezes the exact falsification criterion
and primitive-contract hash. The oracle capability includes the canonical
criterion digest and primitive-contract digest, but no raw prediction values,
geometry, `B`, `F`, or positive-map payload; it independently reconstructs the
stationary/Drazin response.
The capability payload has a canonical SHA-256 bound to the criterion and
primitive contract. The criterion ID and comparison rule are a closed reviewed
schema, and its positive-inference flag must be an exact false Boolean. Any
extension or positive-map criterion is refused before `PREDICTION_LOCKED`.
The oracle result must have an exact closed dictionary schema with exact
`Fraction` triples. G8 and G9 compare its `B,F` records directly to separately
frozen formal values, and the reviewed oracle callable identity is bound before
execution. Every authoritative top-level certificate record has an independent
reviewed canonical-byte digest, so a patched runtime producer cannot redefine
its own acceptance reference. In particular, the T1 tangent-Gram and SLD-metric
determinants are parsed as exact fractions and must be strictly positive.

Deterministic artifact provenance binds the canonical bytes of the repository's
`requirements.test.txt` dependency declaration. Installed Python and Typer
versions are deliberately excluded from artifact acceptance bytes: they are
environment diagnostics, not proof identity or verification authority.
The exact lexical policy path, closed record schema, field types and values, and
an independently reviewed canonical record digest are checked by both artifact
construction and disk verification.

## G0-G13

- **G0:** exact configuration, full control box, and no runtime defaults.
- **G1:** identical `W`, source, and stationary branch for geometry/counting/response.
- **G2:** derived no-reset/Lindblad premises, exact center contraction/Drazin
  bounds, T0 delta-box uniqueness, and explicit uniform floors.
- **G3:** exact Drazin and first/second branch derivative identities.
- **G4:** actual-branch projective/SLD geometry; no auxiliary state map.
- **G5:** count orientation, `W_q|_0=W`, trace preservation, and `J=partial_q W_q|_0`.
- **G6:** frozen exact `B` and `F`; no finite-difference authority.
- **G7:** refusal only of same-curvature and frozen zero-preserving homogeneous
  `Omega`-only maps; other map classes remain open.
- **G8:** separately authenticated geometry, counting, and oracle source lanes.
- **G9:** prediction locked before oracle; positive constitutive inference refused.
- **G10:** conventions, closure, units, zero sets, and local/global scope.
- **G11:** reverse-count and zero-current/null controls.
- **G12:** exact reversal, qanti/factor-two algebra, and local-curvature scope.
- **G13:** immutable registry and exact claim semantics. Disk publication is
  separately required and verified by guarded `status`/`verify` APIs.
