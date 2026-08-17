# Three-dimensional constitutive-map proof contract

## Scope and status

This experiment is an internal analytic classification program. A successful
execution reports `PASS_INTERNAL_ANALYTIC`, `NO_EMPIRICAL_EVIDENCE`, and
`MODEL_SPECIFIC_RELATIONS_ONLY`. It does not establish a universal response
law, full CWT behavior, physical units or dynamics, field evidence, or an
empirical CGT/response alignment.

The two positive cases are deliberately separate. QP3 is a same-operator
spectral calibration and is not a finite-speed CWT response. BC3 is a synthetic
fixed-tick response family and does not obey a scalar Omega-only law.

## BC3: Benchmark-C kinetic control

Controls are `(u,v,alpha)` on

```text
D = [1/20,3/20] x [1/20,3/20] x [3/10,2/5].
```

The theorem uses experiment-local exact formulas copied from and hash-bound to
the authored Benchmark-C `C0` source, with fixed readout gain `9/20`. A live
core comparison at four points is only a regression and has no uniform or
acceptance authority. Analytic full-box bounds give clip margin `1/8` and phase
range `[349/8000,1101/8000]`, so kernel clips and phase wrapping are inactive
on `D`; no
alternate branch, continuation, scheduler, noise, or repaired state is
admissible. The unwrapped update is

```text
x_(k+1) = x_k + alpha_k [theta(u_k,v_k)-x_k].
```

It uses equilibrium initialization, stored right endpoints, update-then-sample,
and the exact reverse of the stored forward controls. The uniform contraction
factor is at most `7/10`. The geometry-blind readout is the independently
declared Benchmark-C circulation difference from instantaneous equilibrium.

Let `J_x` be the phase gradient of that readout, `eta=J_x dot dtheta`, and
`m=(1-alpha)/alpha`. The predictor is frozen before response-oracle access:

```text
beta = -m eta,
F = d beta = alpha^-2 d alpha wedge eta - m d eta,
vector(F) = (F_v_alpha,F_alpha_u,F_u_v).
```

The branch state `psi(p,theta)` is alpha-independent, so
`Omega=Omega_u_v du wedge dv` and its three-vector has rank one. Directed
rational interval enclosures of the exact exponential/trigonometric formulas
must prove the held-out response components and density nonzero. Identical
Omega at `alpha=3/10` and `alpha=2/5` with different response tensors rejects a
scalar Omega-only fiber law.

The held-out center is `(3/25,2/25,1/3)`. Tangents
`t1=(2,-1,0)` and `t2=(2,0,-1)` give area vector `t1 cross t2=(1,2,2)`.
No coordinate-plane response from this center is available to calibration.
The analytic prediction is hash-locked before a separate oracle runs the
oblique loops. Access follows exactly `INIT -> PREDICTION_LOCKED -> ORACLE_RUN
-> VERIFIED`; stale/replayed locks, reordered calls, predictor access after the
oracle, and wrapper bypasses poison the session.

The reviewed scales and edge resolutions are

```text
(s,N) = (1/400,1024), (1/800,4096),
        (1/1600,16384), (1/3200,65536).
```

The first two are development regressions and the last two are locked
synthetic holdouts. The exact lattice retains state across corners, samples
each right endpoint once, samples the closing point once, and initializes the
reverse independently at equilibrium. The generic compact-C3 proof gives

```text
B(s,N) = 111/(500 s N) + 1591/(500 N) + 14 s.
```

The predictor seals an independently directed midpoint line interval `L` and
center-form interval before oracle access. The oracle uses a no-libm,
round-to-nearest binary64 interval kernel with adjacent-float rational input
bounds, outward `nextafter` after every operation, exact lattice phase
differences, degree-14 exponential/cosine and degree-13 sine polynomials with
reviewed remainders, and deterministic balanced pairwise sums. Each row must
conjunctively have density-interval width at most `1e-6`, negative upper bound,
`Qanti-L` inside the reviewed dynamic remainder, `L/s^2-F(c)` inside the local
remainder, and `Qanti/s^2-F(c)` inside `[-B,B]`. Missing authenticated
enclosures are `INDETERMINATE`; a finite violation is `FAIL`. No fitted slope,
output-selected threshold, or orientation-remainder cancellation is allowed.
The legacy scalar float recurrence is retained only as
`NON_AUTHORITATIVE_DIAGNOSTIC`. It evaluates a different floating-control and
libm path, is never unioned into or used to widen the authoritative interval,
and is not a formal-PASS input. It records containment, signed midpoint
residual, and distance to the exact-lattice interval. The exact
development-selected ceiling `1/1000000` in density units is only an
implementation-drift sentinel, not mathematical uncertainty. Finite drift at
or below that ceiling is `PASS_NONAUTHORITATIVE_REGRESSION`. Nonfinite or
over-ceiling drift preserves the formal interval result and theorem gates but
blocks artifact publication and CLI PASS as `BLOCKED_DIAGNOSTIC_DRIFT`.

Gain zero is an exact full response null. `alpha=1` is the scoped `u-v`
response null. A pure-alpha loop is null because the branch target is fixed.
Ordinary orientation difference is exactly twice `Qanti` by definition.

The BC3 disposition is
`SAME_MODEL_KINETIC_CONTROL_GEOMETRY_KERNEL_SEPARATION`.

## QP3: ambient same-operator calibration

QP3 is experiment-local. It is not `cwt.operator.L_map.qp1_builder`, whose
two-dimensional chart has a variable gap. For `lambda in R3\{0}` let

```text
n = lambda/|lambda|,
P+ = (I+n dot sigma)/2,
H = 3/5 I + 2/5 P+.
```

The eigenvalues are `1` and `3/5`, with gap `2/5`. Geometry and spectral
response live in separate modules that share only `H`, `dH`, and `P+`.
In the repository convention,

```text
Omega_ij = epsilon_ijk lambda_k / (2 |lambda|^3).
```

The independent Kubo lane uses

```text
K_ij[O] = 2 Im <+|O_i|-><-|partial_j H|+> / gap^2.
```

For independently declared `O_i=+partial_i H`, half antisymmetrization gives
`+Omega`. The conventional `-partial_i H` gives `-Omega`; full
antisymmetrization is exactly twice the half convention.

At centers `e1,e2,e3`, the two-form vectors are `e_i/2` and span rank three
across centers. This is not a claim that the projective branch Jacobian is rank
three: radial scale is redundant. At held-out `h=(1,2,2)/3`, the oblique normal
is also `h` and the independently computed density is exactly `1/2`. No
response fitting is permitted.

Exact Pauli multiplication and projector algebra own acceptance. Explicit
north/south spinors differ by transition `exp(-i phi)`, their patch
curvatures agree, the monopole form has `dOmega=0` away from the origin, sphere
flux `2 pi`, and Chern number `+1`; therefore one global smooth connection is
unavailable. A computed constant projector is an exact zero control. The
nonscalar constant map `diag(2,1,1)` produces exact divergence `1/3` at `h` and
is refused as a curvature map. Numerical spectral and covariance evaluations
are regressions only.

The QP3 disposition is
`SAME_OPERATOR_SAME_CONNECTION_FULL_RANK_CALIBRATION_ONLY`, where “full rank”
means the center two-form-vector design, not the branch Jacobian.

## Firewalls and refusals

The BC3 primitive, predictor, midpoint, oracle, lattice, and interval modules
have separately authenticated normalized-AST lanes. Direct, relative, aliased,
star, and dynamic imports, attribute aliases, and normalized forbidden local or
parameter names fail closed. The response oracle imports neither predictor nor
geometry and receives no connection, curvature, flux, area, orientation label,
outcome, or held-out response. The QP3 Kubo lane derives only from authenticated
`H`, `dH`, projector, and spectral inputs and imports no geometry module.
Artifacts bind independently fingerprinted gate ownership, dispositions,
claims, clean-import paths, material sources, source roles, and recursive
predecessor artifact inventories. Every path component from the volume root is
link/reparse checked; unsafe or overlapping destinations are refused before any
byte is written.

The program refuses: a two-dimensional pointwise quotient presented as a
prediction; the authored `beta=2A` P1 oracle; gain/readout scaling as a third
control; private tilt/chirality branch knobs; auxiliary or finite-step branches;
geometry-fed response; held-out response or identifier leakage; arbitrary
tensor fitting; same-center basis measurement followed by a pseudo-held-out
oblique projection; and forged statuses, registries, artifacts, or claims.
