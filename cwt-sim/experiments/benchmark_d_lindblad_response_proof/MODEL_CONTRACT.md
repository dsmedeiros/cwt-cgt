# Benchmark D continuous Lindblad response theorem contract

## Status and claim ceiling

This package proves one internal analytic specialization and reports
`PASS_INTERNAL_ANALYTIC / NO_EMPIRICAL_EVIDENCE` only when every executable gate
passes.  It is an authored five-state model with an authored readout.  It is not a
physical validation, an empirical result, a derived continuum limit of CWT, or a
CGT alignment result.  Its numerical checks are implementation regressions; the
acceptance argument is analytic.

The package binds `cwt.cgt.lindblad.lindblad_rhs` and
`lindblad_superoperator`, but the theorem path never calls the Euler-plus-PSD
helpers `apply_lindblad_step` or `lindblad_branch_density`.

## Frozen model

Use Benchmark D branch D0 with controls `(b,d)` on

```text
b in [1/100,1/20],  d in [41/200,49/200],  center=(3/100,9/40).
```

Set `k_+=d+b`, `k_-=d-b` and construct the five-state reflecting random-walk
kernel `K` directly.  The box gives

```text
k_->=31/200, k_+<=59/200, 1-2d>=51/100.
```

Thus the core clips at `.02` and `.46` are inactive, with margins `.135` and
`.165`.  The named readout is the core `mean_position` operator
`O=diag(1,2,3,4,5)`.

Every `LindbladConfig` field is fixed: `dt=1/50`, `integration_steps=30`,
`coherent_scale=0`, `edge_jump_scale=1/5`, `site_potential_scale=0`,
`depolarizing_rate=1/25`, `dephasing_values=(3/10,)`,
`coherence_switch_floor=1/5`, and `scan_mesh=9`; the actual dephasing is `3/10`.
The Euler clock fields are recorded for core identity only and do not define the
analytic flow.

On diagonal density matrices the exact core generator reduces to

```text
x_dot = A(b,d)x+c,
A=(1/5)(K^T-I)-(1/25)I,
c=(1/125)1.
```

The package evaluates the core RHS on the complete five-vector diagonal
population basis and the core superoperator on a complete four-vector traceless
diagonal deviation basis, at all four box corners and the center. Equality is
required on this diagonal invariant subspace; no full-superoperator equivalence
is claimed. Omitting `c` is a model change and fails closed.

## Uniform stability and true stationary branch

The jump-plus-dephasing semigroup is CPTP and contractive in trace norm.  On
traceless Hermitian deviations, depolarization factors the evolution by
`exp(-(t-s)/25)`, hence

```text
||U(t,s)||_1 <= exp(-(t-s)/25), M=1, tau=25, ||A^-1||<=25.
```

No Euler approximation, cache, continuation, or PSD projection enters this
statement.  The fixed branch is the exact rational solution
`xbar=-A^-1 c`.  It has unit trace and zero residual.  From

```text
xbar_i=(5/6)(K^T xbar)_i+1/30
```

and `K_ii>=51/100`, every component obeys

```text
xbar_i >= (1/30)/(1-(5/6)(51/100)) = 4/69.
```

The separately reported 3x3 box sample is only a diagnostic; `4/69` is the
uniform analytic floor.

## Response one-form and exact center curvature

Center the readout on the true fixed branch,
`r=Tr[O(rho-rhobar)]`.  For `X_i=partial_i xbar`, the continuous contraction
corollary gives

```text
B_i = O^T A^-1 X_i,
F_bd = partial_b B_d - partial_d B_b.
```

All inverses, derivatives, determinants, and adjugates are evaluated over exact
rational arithmetic.  At the frozen center,

```text
F_bd = -28888766872100000000000 / 235345963257301712101
     = -122.7502119529289...
```

This number is recomputed from the model; equality to the reviewed fraction is a
gate rather than a substitute for computation.  The identity readout gives zero,
and multiplying `O` by `a` multiplies `B` and `F` by `a` exactly.

## Loop, orientation, and continuous model-time integral

The positive path is

```text
gamma_+(u)=c+s(cos(2*pi*u),sin(2*pi*u)), 0<=u<1,
s=1/100,
gamma_-(u)=gamma_+(1-u).
```

The slow drive uses the exact structured clock
`uniform_affine_normalized_clock_v1`:

```text
u=t/T,
lambda_+(t)=gamma_+(u),
lambda_-(t)=lambda_+(T-t)=gamma_+(1-u), 0<=t<=T.
```

Thus `sup_t ||lambda_dot|| <= 2*pi*s/T` and
`sup_t ||lambda_double_dot|| <= (2*pi)^2*s/T^2`. These are the speed and
acceleration factors used in the `C(s)/T` proof. A nonuniform
reparameterization, arbitrary schedule, missing clock declaration, or altered
endpoint/reverse convention is outside the theorem contract and fails closed.

The stored diagnostic sequence does not duplicate the closing endpoint.  The
trajectory, if ever evaluated, starts at the exact instantaneous equilibrium and
uses the projection-free continuous affine flow.  The response is

```text
Q=integral_0^T Tr[O(rho(t)-rhobar(lambda(t)))] dt,
Qanti=(Q_+-Q_-)/2.
```

The generator rates have units of inverse model-time, `T` has units of
model-time, the `mean_position` readout is a dimensionless site-index mean, and
`Q` has units of mean-position-index times model-time. No external clock or
readout calibration is present, so this is not yet physical time or a calibrated
physical observable.

For exact reversal, the ordinary orientation difference is `Q_+-Q_-=2 Qanti`.

## Directed interval and dynamic remainder certificate

The implementation expands `det A`, `adj A`, both rational response components,
and `F_bd` as exact bivariate polynomials.  It translates each polynomial to the
loop center and performs exact rational interval arithmetic on the enclosing
square `|b-b0|,|d-d0|<=s`.  Since the resulting curvature interval is strictly
negative, Stokes' theorem and the rational bounds `333/106 < pi < 355/113`
give a strictly negative enclosure for

```text
L(s)=oint B=integral_disk F_bd db dd.
```

Let `e=x-xbar` and
`g(u)=A(lambda(u))^-1 partial_u xbar(lambda(u))`.  Variation of constants,
the trace-norm propagator bound, and equilibrium initialization give, separately
for each orientation,

```text
|Q(T)-L(s)| <= ||O-3I||_infinity * tau
               * (||g(0)||_1 + integral_0^1 ||g'(u)||_1 du) / T
             = C(s)/T.
```

The same bound applies to `Qanti` because the half sum of the two orientation
errors is no larger than `C(s)/T`. `C` has units
readout-times-model-time squared, so
`C/T` has the units of `Q`.  Every factor in `C(s)` is bounded from the exact
rational response-vector polynomials; no trajectory or fitted slope selects the
threshold.

For `s=1/100`, freeze the conservative power-of-two rule

```text
T0 = 2^ceil(log2(4*C(s)/L_min(s))),
```

where `L_min` is the certified lower magnitude of the line integral.  The current
exact certificate gives `T0=1,048,576`.  A fixed-scale ladder doubles `T`; a
joint ladder halves `s` and quadruples `T`, so `s*T/tau` doubles and the certified
remainder-to-line ratio strictly decreases.  These large durations are theorem
bounds, not claimed practical simulation times.  No trajectory is used to pass
C12.

## Projective no-go control

Separately from the current core helper `BranchState` geometry, define the
smooth auxiliary normalized positive-real D0 map

```text
psi_j(b,d)=sqrt(p_j),
p_j proportional to ((d+b)/(d-b))^j.
```

It is channel-equivalent for this frozen generator only because `p` and `theta`
are inactive when both coherent and site-potential scales are zero. It is not
the actual geometry returned by the current core branch helper. It is smooth and
strictly positive on the box. Because `psi`, `partial_b psi`,
and `partial_d psi` are real, the projective curvature
`Omega_bd=2 Im <D_b psi|D_d psi>` is exactly zero.  The response construction
above has nonzero `F_bd`.  This is only a no-universal-alignment counterexample:
response curvature does not imply projective curvature.  It is not evidence for
or against any substrate-level CGT law.

## C1-C13 and fail-closed policy

Every live gate belongs to at least one of C1-C13, the live gate set must equal
the registered union exactly, and each case disposition is derived from its
owned gates.  A failed gate changes its case disposition and the overall state to
`FAIL_INTERNAL_ANALYTIC`.  Artifact writing and CLI success are forbidden in
that state.  Required nulls/refusals include identity and scaled readouts, zero
depolarization, Benchmark-C `I/3`, omitted affine source, nonzero coherent/site
terms, Euler/PSD flow, and mutated timing/reversal/initialization.

## Phase 11 relationship

Tracked Phase 11 is a historical Lindblad-style exploratory scaffold.  It uses
finite Euler stepping, PSD projection, cached finite-step branch densities, and
mean/final-sample loop responses.  Those outputs do not instantiate this
continuous model-time theorem. This package supersedes only the narrow
Benchmark-D analytic question under the explicit specialization above; it does
not retroactively validate Phase 11 fits or its broader interpretations.
