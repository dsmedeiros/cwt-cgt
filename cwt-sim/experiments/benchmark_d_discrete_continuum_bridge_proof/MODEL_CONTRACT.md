# Benchmark D rational discrete/continuous bridge contract

## Status and claim boundary

This package is an internal analytic proof program over an abstract exact-
`Fraction` D0 diagonal population family. A successful run has the
disposition `PASS_INTERNAL_ANALYTIC` and the evidence status
`NO_EMPIRICAL_EVIDENCE`. It proves only an exact bridge between two authored
five-state D0 diagonal-population models with the named mean-position readout.
It does not prove a full-density channel limit, scheduler behavior, calibrated
physical time, empirical validity, a CGT alignment law, or general CWT.

The previously frozen discrete (`h=9/50`, `q=1/125`) and continuous artifacts
are immutable structural context. The old discrete point is not on the primary
family because `delta*h=9/1250`, not `1/125`; it is not numerically bridged by
this theorem.

## 1. Frozen D0 family

Let `x` be a column population vector on five sites. Controls are

- `b in [1/100,1/20]`,
- `d in [41/200,49/200]`,
- center `c=(3/100,9/40)`.

The unclipped row-stochastic D0 kernel has right/left probabilities `d+b` and
`d-b`, with reflecting end sites. Write `R=K^T-I`, `a=1/5`, `delta=1/25`, and
`u=(1/5)1`. The theorem family is rational `0<h<=1/5` with

```text
q_h = delta h,
E_h(x) = (1-q_h)(I+h a R)x + q_h u
       = M_h x + c_h,
M_h = (1-delta h)(I+h a R) = I+h A_h,
c_h = h (delta/5) 1,
A_h = a(1-delta h)R-delta I.
```

The associated continuous generator at edge rate `e` is

```text
A(e)=e R-delta I,       c=(delta/5)1.
```

Thus `A_h=A(a_h)` with `a_h=a(1-delta h) in [124/625,1/5]`.
On the frozen D0 box, `||K^T-I||_1<=49/50`, so the exact generator and
source errors relative to `A=(1/5)(K^T-I)-delta I`, `c=(delta/5)1` are

```text
||A_h-A||_1 <= (49/6250)h,       c_h/h-c=0.
```

Fixed or exponential `q`, the historical off-family point, nonzero coherent or
site-potential terms, zero `delta`, iterative fixed points, and branch helpers
are outside this proof.

All core configuration fields are explicit. Finite provenance/regression calls
use `dt=h`, edge scale `1/5`, depolarizing `delta*h`, actual dephasing `3/10`,
zero coherent/site scales, and the named
`mean_position=diag(1,2,3,4,5)` observable. Their representable runtime domain
is frozen to `1/10^12<=h<=1/5`; smaller `h` is refused before a float cast can
underflow. These calls are not a proof of uniform runtime equivalence. The
uniform theorem is supplied only by the exact symbolic affine identity above.
Dephasing cancels on the diagonal subspace but remains in the Kraus safety
margin. Neither `effective_branch_density` nor `fixed_point_density` is called.

## 2. CP/TP, support, and contraction

On the complete box, `d-b>=31/200` and `d+b<=59/200`; no D0 clip is active.
At `h=1/5`, the maximum jump-plus-dephasing loss is

```text
h [3/10 + (1/5)(2d)] <= 199/2500,
```

so the no-jump radicand is at least `2301/2500`. This is far below the core
rescale threshold `49/50`; the exact Kraus completeness relation is preserved.
The finite core regression checks all four box corners plus center, the complete
five-vector population basis, and a complete four-vector traceless diagonal
basis at three representable `h` values. It is provenance/regression only and
makes neither a uniform runtime nor a full-superoperator equivalence claim.

On zero-sum populations the stochastic part is nonexpansive in `l1`, hence

```text
||M_h v||_1 <= (1-delta h)||v||_1,
(1-delta h)^k <= exp(-delta k h),
h ||(I-M_h)^(-1)||_1 <= 1/delta = 25.
```

The fixed branch is the exact rational solve
`xbar_h=-A_h^(-1)c`, not an iteration. The analytic population floor is `4/69`
(not the one-step injection `q_h/5`). Since `||R||_1<=2`,

```text
||xbar_h-xbar||_1 <= ||A_h^(-1)||_1 |a_h-a| ||R xbar||_1
                   <= 25 (h/125) 2 = 2h/5.
```

Writing `L_b=2`, `L_d=4`, exact differentiation gives
`||X_h,i||_1<=5 L_i` and `||X_h,ij||_1<=50 L_i L_j`. These
uniform analytic inequalities—not the optional finite `h` cross-check—supply
the required `C2` control.

## 3. Exact one-form and curvature bridge

Let `H=(1,2,3,4,5)` and center the readout by the instantaneous exact fixed
branch. For the continuous affine generator,

```text
B_CT,i(e)=H A(e)^(-1) partial_i xbar(e).
```

For the right-endpoint update-then-sample discrete theorem,

```text
B_h,i=-H(I-M_h)^(-1)M_h partial_i xbar_h
     =(1/h) B_CT,i(a_h)+H partial_i xbar_h,
h B_h=B_CT(a_h)+h d(H xbar_h).
```

The second term is an exact gradient. It has zero curl and integrates to zero
on every closed loop. Therefore, exactly,

```text
h F_h = F_CT(a_h).
```

The implementation constructs the determinant, adjugate, response numerator,
and curvature numerator over exact `Fraction` polynomials. A directed interval
on `0<=h<=1/5` proves the curvature is negative. At `h=0` it recomputes the
independent formal oracle

```text
F_CT = -28888766872100000000000 / 235345963257301712101
     ~= -122.750211952929.
```

The exact first coefficient is

```text
228322311704703213246688000000 /
44415389442843585257542657921 ~= 5.14061262478678.
```

A directed derivative enclosure is strictly below `88`; the mean-value theorem
therefore gives the uniform theorem-grade bound `|hF_h-F_CT|<88h`. No fitted
slope or finite ladder establishes this identity or limit.

## 4. Loop, units, and fixed-time response bridge

The theorem scale domain is exact rational `0<s<=1/100`; the registered report
uses `s=1/100`. Every such circle is contained in the D0 box. At the maximum
scale its exact extrema are `b in [1/50,1/25]` and
`d in [43/200,47/200]`, leaving `1/100` to every box face. The common CCW
circle has affine normalized clock `u=t/T` and exact reverse
`lambda_-(t)=lambda_+(T-t)`. The discrete path stores no duplicate initial
point and processes the closing endpoint exactly once. `N=T/h` must be a
positive integer. Initialize the discrete run at `xbar_h(lambda(0))` and the
continuous run at `xbar(lambda(0))`.

Let the raw discrete sum be `S_h` and its model-time-scaled response be `Q_h`:

```text
S_h = sum_(n=1)^N H[x_n-xbar_h(lambda_n)],
Q_h = h S_h.
```

`H` is a dimensionless site-index readout; `h,T` are uncalibrated model-time;
`Q` has mean-position-index times model-time units. No physical-time claim is
made without an external clock/readout calibration.

The executable certificate stores these premises as exact rational coefficients,
integer powers, and booleans rather than accepting formula prose. It recomputes
the circle extrema, scale-domain margins, initialization, clock, contraction,
reversal, endpoint, common-path, and `Q_h=hS_h` requirements before PASS. The
local defect estimate

```text
C_loc = 76/625 + 6 pi s/(5T)
```

together with the contraction product and right-Riemann variation proves, for
each orientation,

```text
|Q_h^+/- - Q_CT^+/-|
  <= h[(214/25)T + 120 pi s]
  <= h[(214/25)T + (42600/113)s],
```

where `pi<=355/113`. The same bound holds for
`Qanti_h=(Q_h,+-Q_h,-)/2`. The ordinary scaled orientation difference is exactly
`2 Qanti_h`. Safe component inequalities `640h` and `1280h` are auxiliary; no
full-Kraus `O(h)` observation affects PASS.

The primary result is the iterated limit

```text
lim_(T->infinity) [lim_(h->0, T/h integer) Qanti_h(T)] = L_CT.
```

An optional scale limit within `0<s<=1/100` may follow. The displayed constants
and box-containment margin are uniform on that declared domain. This proof does
not commute limits. A
sufficient simultaneous condition derived from the displayed bound is
`T->infinity` and `hT->0`; area-relative shrinking additionally requires
`sT->infinity` and `hT/s^2->0`. A finite ladder, `Ns->infinity` alone, a
T-first alternative, or an unqualified joint/interchange claim is refused.

## 5. Fail-closed cases and context

Every live theorem gate is owned by at least one dynamic C1-C12 case, and the
live-gate set must equal the registered set. Test-only gate overrides are
monotone fail-only: `True` cannot rescue a naturally failed gate. Artifact
writing and verification recompute semantic disposition and fail unless all
gates and expected case dispositions pass.

The refusal registry covers fixed/exponential `q`, wrong parameter scaling,
missing affine source or transpose, wrong response `h`, wrong centering,
clock/reversal/endpoint mismatch, incomplete diagonal identity, active safety
branches, iterative fixed points, false `q/5` floor, per-tick gap reuse,
finite-ladder proof, unproved joint limits, provenance omissions, helper/Euler
dependence, and claim inflation.

The strict-LF artifact bundle binds a portable source-text closure and the raw
bytes of recursively inventoried, path-bound prior discrete and continuous
artifact bundles. Any nested addition, omission, path/type substitution,
symlink, or Windows reparse entry is rejected without traversal. Those bundles
are context only and are never regenerated or executed by this experiment.
