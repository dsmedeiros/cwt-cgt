# Contractive loop-response theorem and CGT alignment no-go result

## Status and claim ceiling

This document gives a finite-dimensional analytic theorem, its proof, an exact
realizability/no-go theorem, and deterministic authored fixtures. The executable
disposition is **`PASS_INTERNAL_ANALYTIC` / `NO_EMPIRICAL_EVIDENCE`**. Numerical
fixtures check implementations and rates; they do not prove the analytic
statements and they are not a study, experiment, preregistration, external
validation, or evidence that CWT/CGT predicts a physical response.

The result applies to the declared uniformly contractive class below. It does
not prove that every CWT update is contractive, that its branch is smooth, that
the repository has a continuous-time CWT limit, or that response curvature is
aligned with the pullback quantum-geometric curvature.

## 1. Discrete contractive response theorem

Fix a coupling/readout condition `c`. Let `lambda` range in a finite-dimensional
parameter chart and let the state use one fixed norm. The timing convention is
right-endpoint **update then sample**:

```text
x_n = F_c(x_(n-1), lambda_n),
q_(c,n) = r_c(x_n, lambda_n),
Q_c = sum_(n=1)^N q_(c,n).
```

Assume:

1. `F_c` and `r_c` are `C3` on a compact tube containing the driven branch.
2. There is a smooth fixed equilibrium branch
   `xbar_c(lambda)=F_c(xbar_c(lambda),lambda)`.
3. In the same fixed norm throughout the tube,
   `||D_x F_c|| <= rho < 1` uniformly. This is stronger and more explicit than
   a pointwise spectral-radius condition.
4. The readout is centered:
   `r_c(xbar_c(lambda),lambda)=0`.
5. `lambda_n=gamma(n/N)`, where `gamma` is a closed piecewise-`C2` path with
   finitely many fixed corners. The reversed protocol is the exact sequence
   `gamma_-(t)=gamma_+(1-t)` with the same endpoint convention.
6. The initial error is `||x_0-xbar_c(lambda_0)||=O(1/N)`. Exact equilibrium
   initialization is included.

On the branch define

```text
M_c(lambda) = D_x F_c(xbar_c(lambda), lambda),
H_c(lambda) = D_x r_c(xbar_c(lambda), lambda),
X_(c,i)(lambda) = partial_i xbar_c(lambda),
B_(c,i) = -H_c (I-M_c)^(-1) M_c X_(c,i).
```

The inverse exists uniformly because `||M_c|| <= rho < 1`, with
`||(I-M_c)^(-1)|| <= 1/(1-rho)`.

### Theorem 1

Under assumptions 1–6,

```text
Q_c(gamma,N) = integral_gamma B_c + O(1/N),
```

uniformly over a compact family with common derivative and contraction bounds.
The constant depends on the declared norm, tube, branch, path regularity,
coupling, and readout. It is not universal.

### Proof

Write `e_n=x_n-xbar_c(lambda_n)` and
`Delta lambda_n=lambda_n-lambda_(n-1)`. Taylor expansion at the right endpoint
gives, uniformly on the tube,

```text
e_n = M_(c,n)e_(n-1) - M_(c,n)X_(c,i)(lambda_n) Delta lambda_n^i
      + R_n,
||R_n|| <= K(||e_(n-1)||^2 + ||Delta lambda_n||^2
             + ||e_(n-1)|| ||Delta lambda_n||).
```

Uniform contraction and the discrete variation-of-constants formula give
`sup_n ||e_n||=O(1/N)`. Subtract the instantaneous stable corrector

```text
l_n = -(I-M_(c,n))^(-1) M_(c,n) X_(c,i)(lambda_n)
      Delta lambda_n^i.
```

The recurrence for `e_n-l_n`, geometric-series summability, and piecewise-`C2`
regularity show that its summed contribution is `O(1/N)`; the finitely many
corners only change the constant. Centering and a second Taylor expansion give

```text
r_c(x_n,lambda_n)
  = H_(c,n)e_n + O(||e_n||^2)
  = B_(c,i)(lambda_n) Delta lambda_n^i + epsilon_n,
sum_n |epsilon_n| = O(1/N).
```

The right-endpoint one-form sum differs from the path integral by `O(1/N)`.
Adding the two bounds proves the theorem. This proof is a standard contraction
and discrete summation argument; the executable fixture only illustrates it.

## 2. Orientation, interaction, Stokes, and factor two

For the exact reversed path, the line integral changes sign. Define

```text
Q_(anti,c) = (Q_(c,+)-Q_(c,-))/2.
```

Then `Q_(anti,c)=integral_gamma B_c+O(1/N)`. For the complete on/zero
interaction,

```text
D = Q_(anti,on)-Q_(anti,0),
B^D = B_on-B_0,
F_R^D = dB^D.
```

Therefore, for a contractible oriented spanning surface `S`,

```text
D = integral_gamma B^D + O(1/N)
  = integral_S F_R^D + O(1/N).
```

The ordinary difference in differences is

```text
(Q_(on,+)-Q_(on,-))-(Q_(0,+)-Q_(0,-)) = 2D.
```

No step assumes `B_0=0`; the executable interaction fixture deliberately uses
a nonzero zero-coupling one-form.

## 3. Scaled loops and the initialization boundary term

Let `gamma_s(t)=lambda_*+s z(t)` with a uniformly bounded piecewise-`C2`
shape. For exact equilibrium initialization, or more generally initial error
`O(s/N)`, the proof above separates the boundary/corrector transient from the
bulk terms and yields constants independent of small `s`:

```text
|Q_c-integral_(gamma_s) B_c| <= C1 s/N + C2 s^2/N.
```

Since the surface signal is generically `O(s^2)`, area-relative convergence in
this equilibrium-reset regime requires `N s -> infinity`. Merely taking
`N proportional to 1/s` can leave a nonzero relative boundary error. For a
fixed unscaled loop, the statement reduces to `O(1/N)`.

### Separately scoped periodic/endpoint-flat improvement

The stronger estimate is not automatic. Assume in addition either the unique
driven periodic orbit is used or a matched first-order corrector is supplied;
sampling covers one endpoint-consistent full period; the path and branch are
periodic `C3` (or an endpoint-flat `C3` path uses matched corner correctors);
and a discrete
summation-by-parts calculation cancels the first-order boundary term. Then

```text
|Q_c-integral_(gamma_s) B_c| <= C1' s^2/N + C2' s/N^2.
```

The active-loop design must select and justify one of these two regimes. It may
not apply the periodic/endpoint-flat rate to an ordinary equilibrium reset.
The exact linear fixture uses its unique driven-periodic orbit and exhibits an
even stronger `N^-2` cancellation for the selected circle; that special rate
is not promoted to the theorem.

## 4. Continuous-time corollary

Consider `dx/dt=f_c(x,lambda(t))` with a smooth equilibrium branch and the same
centered readout. Do not substitute pointwise Hurwitz stability for stability
of the time-varying driven system. In one declared common norm, require the
variational propagator along every allowed loop to obey the uniform estimate

```text
||U_c(t,u)|| <= M exp(-(t-u)/tau),  t>=u,
```

with common finite `M` and `tau` on the selected family (a common Lyapunov
condition implying this estimate is also sufficient). Here `U_c(t,u)` is the
propagator of the branch-linearized equation
`d(delta x)/dt=J_c(lambda_T(t))*delta x` along every declared slow-duration
family `lambda_T`, with `U_c(u,u)=I`. Separately require uniform frozen-branch
hyperbolicity/invertibility in the same norm,

```text
J_c(lambda)=D_x f_c(xbar_c(lambda),lambda),
sup_(c,lambda) ||J_c(lambda)^(-1)|| <= K_J < infinity.
```

The propagator estimate alone does not imply this inverse bound. The
slow-manifold equation for
`e=x-xbar_c(lambda)` is

```text
de/dt = J_c e-X_(c,i) dot(lambda)^i+O(||e||^2),
```

so the response one-form is

```text
B_(c,i) = H_c J_c^(-1) X_(c,i).
```

Define the physical-time observable exactly by

```text
Q_c[gamma]=integral_0^T r_c(x(t),lambda(t)) dt.
```

For the generic statement initialize at equilibrium,
`x(0)=xbar_c(lambda(0))`. For the stronger statement initialize on the unique
driven periodic orbit or with the proved matched endpoint-flat corrector. The
reverse path is exactly `lambda_-(t)=lambda_+(T-t)` on the same interval and
uses the same endpoint/quadrature convention, with the duplicate closing
endpoint counted once.

For a loop of duration `T` and scale `s`, equilibrium initialization gives a
generic remainder `O(s tau/T)` (plus the bulk terms absorbed in the uniform
constant). Under the periodic/endpoint-flat hypotheses above, it improves to

```text
O(s^2 tau/T + s (tau/T)^2).
```

For `dx/dt=(lambda-x)/tau` with the control held over a sample interval,

```text
alpha(dt) = 1-exp(-dt/tau)
```

is the exact discrete relaxation coefficient. Holding `alpha` fixed while
changing `dt` changes the physical model. This corollary is a stable-ODE
result, **not a derived continuous CWT limit**.

The separate inverse assumption is necessary. For the scalar family
`f(x,lambda)=(-1+lambda)(x-lambda)` driven by `lambda(t)=sin(t)`, the
branch-linearized propagator is

```text
U(t,u)=exp(-(t-u)+cos(u)-cos(t)),
|U(t,u)| <= exp(2) exp(-(t-u)),
```

yet `J=-1+sin(t)` vanishes at `t=pi/2`. The executable negative-assumption
fixture records this counterexample; no `J^-1` formula is asserted there.

## 5. Exact realizability and the alignment no-go theorem

Let `beta=beta_i(lambda)d lambda^i` be any smooth one-form on a chart and fix
`0<rho<1`. Define

```text
x_n = rho x_(n-1)+(1-rho)lambda_n,
r(x,lambda) = -(1-rho)/rho beta(lambda).(x-lambda).
```

The equilibrium is `xbar=lambda`, so `M=rho I`, `X=I`, and
`H=-(1-rho) beta/rho`. Hence

```text
B = -H(I-M)^(-1)MX = beta
```

exactly. Thus every smooth local response one-form is realizable by a smooth
uniform contraction.

Independently choose any normalized projective state map `Psi(lambda)`. On a
gauge patch, augment the response state with real and imaginary coordinates
`y` driven contractively toward a representative of `Psi(lambda)`; use the
block map `(x,y)` and let the readout ignore `y`. The block contraction remains
uniform, `B=beta` is unchanged, and the projective curvature of `Psi` can be
chosen independently. Patch changes affect the representative, not its
projector. Consequently:

```text
Omega != 0  does not imply  F_R != 0,
F_R != 0   does not imply  Omega != 0,
```

and contraction, smoothness, a gap, and a fixed branch cannot imply
`F_R^D=kappa Omega`. Such an equality is an additional constitutive/alignment
hypothesis. Its coefficient must be indexed by the named
`experiment/coupling/readout`; it is not a universal scalar.

## 6. Alignment characterization and error bound

For a smooth finite `kappa` and two-forms `F_R^D` and `Omega`, pointwise
alignment requires:

1. **zero-set compatibility:** `Omega=0` implies `F_R^D=0` wherever the model
   asserts a finite coefficient;
2. **collinearity:** the two forms lie on the same pointwise line;
3. **integrability:** because both curvatures are closed,
   `d kappa wedge Omega=0` where `F_R^D=kappa Omega`.

In two parameter dimensions the two-form space is one-dimensional and the
third condition is a three-form identity, so a pointwise quotient at nonzero
`Omega` is tautological. It is **`INELIGIBLE_TAUTOLOGY`** as a predictive test.
In three dimensions, the vectors
`f_R=(F_23,F_31,F_12)` and `omega=(Omega_23,Omega_31,Omega_12)` must be
collinear across a full-rank set of area directions. A coefficient fitted only
on calibration centers must predict a held-out oblique direction; held-out
pointwise division is forbidden.

If `kappa` is constant on a contractible patch and
`F_R^D=kappa Omega`, then

```text
B^D = kappa A+d chi
```

for local potentials `dB^D=F_R^D` and `dA=Omega`. `A` changes by an exact form
under a state gauge change, and `chi` changes correspondingly. This is a
patchwise statement. On a closed surface with nonzero Chern number, `A` cannot
be a single global smooth gauge; if `B^D` were globally exact, a nonzero
constant `kappa` would also conflict with the nonzero integrated Chern flux.

For an independently frozen coefficient field
`kappa_(experiment,coupling,readout)` define
`E=F_R^D-kappa Omega`. The exact constitutive predictor for variable `kappa`
is `integral_S kappa Omega`, not `kappa(c) Phi`. If the comass of `E` is at
most `epsilon` on `S`, then

```text
|D-integral_S kappa Omega| <= mass(S) epsilon + |r_dynamic|.
```

Here `mass(S)` is the two-dimensional Hausdorff area in the declared parameter
norm, and two-form magnitude is its comass in that norm. If instead the frozen
predictor uses a center value `kappa(c)`, `kappa` is `L_kappa`-Lipschitz on
`S`, `||Omega||_comass <= W`, and `diam(S)=delta`, then

```text
|D-kappa(c) Phi|
  <= mass(S) [epsilon + L_kappa W delta] + |r_dynamic|,
Phi = integral_S Omega.
```

The executable helper checks this additional center-approximation term; it is
not silently absorbed into `epsilon`. The constant-`kappa` display is recovered
with `L_kappa=0`.

For ordinary DID, multiply both sides by two. The dynamic remainder retains
the generic or separately justified improved rate; alignment does not remove
it.

## 7. Frozen cases

- **C1 — `COUNTEREXAMPLE`:** nonzero `Omega`, curl-free response.
- **C2 — `COUNTEREXAMPLE`:** zero `Omega`, nonzero response curvature.
- **C3 — `COUNTEREXAMPLE`:** a normalized CP1 state
  `psi=(sqrt(1-q),exp(i phi)sqrt(q))`, with `q=0.5+0.2x` and `phi=5y`,
  computes `Omega=dx wedge dy` on its safe patch. The independently authored
  response potential `B=(x^2/2)dy` computes `F_R=x dx wedge dy`, so the
  aligned coefficient takes the computed values `-1,0,1`.
- **C4 — `COUNTEREXAMPLE`:** the same computed CP1 `Omega` is held fixed
  while independent readouts `B=c A` compute response tensors for
  `c=-2,0,3`. The projective tensor is also checked against the analytic local
  connection `A=x dy`; it is not merely declared.
- **C5 — `INELIGIBLE_TAUTOLOGY`:** two distinct authored two-dimensional
  response forms are computed and their pointwise quotient reproduces the
  second form identically, demonstrating the one-dimensional two-form space.
- **C6 — `COUNTEREXAMPLE`:** a constant independent projective state computes
  `Omega=0`, while the contraction fixture computes a speed-dependent
  orientation-odd response/remainder and a decaying orientation-even
  transient.
- **C7 — `PASS_LOCAL_INTERNAL`:** gauge invariance and coordinate covariance.
- **C8 — `OUT_OF_SCOPE`:** a fixed-gap non-normal similarity family whose
  normalized right state is real and has zero right-only curvature, while its
  normalized left/right connection has complex curvature `-2+2i`. The current
  pure-state theorem does not claim general biorthogonal coverage. This is the
  proof program's explicit three-dimensional similarity family
  `S diag(0,1,2) S^(-1)` with coefficient `a=1+i`; it is not the adversarial
  review's separate projector parameterization. The two constructions support
  the same scope warning, but the value `-2+2i` belongs only to this fixture and
  is not attributed to the alternative example.
- **P1 — `PASS_LOCAL_INTERNAL`:** a deliberately aligned oracle/positive
  implementation control with frozen `F_R=2 Omega`, rank-three
  coordinate-plane areas, and an oblique held-out direction. It is not an
  independently measured response and supplies no empirical evidence.

## 8. Literature position

This repository-specific synthesis sits beside, rather than superseding:

- Bradford and Kovchegov, “Adiabatic Times for Markov Chains and
  Applications,” *Journal of Statistical Physics* 143 (2011),
  [doi:10.1007/s10955-011-0219-6](https://doi.org/10.1007/s10955-011-0219-6),
  which proves adiabatic results for time-inhomogeneous Markov chains.
- Sinitsyn and Nemenman, “Universal Geometric Theory of Mesoscopic Stochastic
  Pumps and Reversible Ratchets,” *Physical Review Letters* 99, 220408 (2007),
  [doi:10.1103/PhysRevLett.99.220408](https://doi.org/10.1103/PhysRevLett.99.220408),
  which derives geometric contributions for stochastic pump observables.
- Pluecker, Wegewijs, and Splettstoesser, “Gauge freedom in observables and
  Landsberg's nonadiabatic geometric phase,” *Physical Review B* 95, 155431
  (2017),
  [doi:10.1103/PhysRevB.95.155431](https://doi.org/10.1103/PhysRevB.95.155431),
  which emphasizes that the pumping connection belongs to the transported
  observable and differs from the state's Berry phase.

No priority or broad novelty claim is made beyond the repository-specific
finite-dimensional contraction proof, exact realizability construction, and
their use to delimit the CWT/CGT claim.
