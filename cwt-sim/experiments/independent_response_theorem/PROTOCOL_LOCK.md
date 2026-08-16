# Geometry-blind-response discrete theorem: protocol lock

## Scope and status

This is a locked **internal synthetic/analytic benchmark-C fixture**. It is not
an external-data experiment, preregistration, untouched holdout, transported
charge measurement, or claim of a physical pump. Both the cycle-sum estimand
and the numerical acceptance thresholds were chosen after an exploratory
square-loop refinement probe at center `(0, 0)`. Every benchmark-C
configuration used here is therefore a discovery/analytic fixture. Passing
this protocol leaves the central empirical/external CWT claim **proof
incomplete**.

The directory name `independent_response_theorem` uses "independent" only to
mean that response is calculated without geometry or orientation inputs. It
does **not** mean independent empirical validation. The report therefore uses
the less ambiguous label "geometry-blind response."

No auditable external raw paired-loop data, frozen manifest, checksum, and
independent measured response are runnable from the repository. That is the
external-data blocker; this harness does not substitute generated benchmark
states for those data.

## Locked tick semantics and estimand

- The clock is discrete with `dt = 1` current tick.
- `phase_relaxation = alpha = 0.35` is fixed per tick.
- Increasing `steps_per_segment = m` lengthens the cycle to `4m + 1` samples
  and makes the parameter path slower. It does not hold a physical cycle period
  fixed.
- The first point is processed and the explicitly duplicated closing endpoint
  is processed, exactly as in the legacy benchmark-C trace.
- The legacy mean response remains unchanged:

  `response = mean(C(actual)) - mean(C(branch)) = mean(q_t)`.

- The additional estimand is

  `Q = sum_t q_t`,

  named `discrete_cycle_sum_surrogate` and measured in
  circulation-current-ticks. It is not called transported charge.
- Orientation summaries use

  `Q_anti = (Q_CCW - Q_CW) / 2` and `Q_even = (Q_CCW + Q_CW) / 2`.

The response API receives only the continued branch states, their path,
`alpha`, and `current_phase_gain`. It receives no signed area, orientation
label, Berry flux, curvature, or fitted coefficient. Geometry is calculated
after the response trace.

## Exact recurrence and tangent limit

Let `theta_t` be the fixed C0 branch phase, `a_t` the relaxed phase after tick
`t`, `e_t = a_t - theta_t`, and `q = 1 - alpha` (this scalar `q` is distinct
from the current-difference sample `q_t`). In the no-wrap chart,

`a_t = a_(t-1) + alpha (theta_t - a_(t-1))`

gives the exact recurrence

`e_t = q e_(t-1) - q Delta theta_t`,

where `Delta theta_t = theta_t - theta_(t-1)` and `e_0 = 0`. The executable
check evaluates the wrapped residual but also requires all increments and lags
to remain below `0.1` radians, so the selected branch stays within a single
unwrapped chart.

For the benchmark-C circulation `C(p, theta, K, gain)`, the code evaluates its
exact node-phase gradient. The C0 phase tangent is analytic, and the response
one-form is

`B_i = -(1 - alpha) / alpha * grad_theta(C) dot partial_i(theta)`.

Assume a fixed branch, a no-wrap phase chart, a uniformly sampled piecewise
`C^2` closed path with finitely many corners, bounded first/second branch
derivatives, and a smooth circulation current. Then `Delta theta_t = O(1/m)`,
the stable recurrence gives `e_t = O(1/m)`, and Taylor expansion gives

`q_t = grad_theta(C_t) dot e_t + O(1/m^2)`.

Away from the finitely many start/corner transients,

`e_t = -(1 - alpha) / alpha * Delta theta_t + O(1/m^2)`.

The transient contribution is `O(1/m)` after summation, as is the accumulated
Taylor/reconstruction error. Consequently, for a fixed loop,

`Q = integral_loop B_i d lambda^i + r_m`, with `r_m = O(1/m)`.

This rate is a theorem for this explicit stable fixed-tick recurrence under the
listed assumptions; it is not a general CWT response theorem. Cyclically
changing the duplicated loop's start changes the finite-`m` transient but not
the limiting line integral.

## Separately computed geometry and 2D quotient consistency

The tangent response curvature is evaluated with central differences:

`F_R = partial_u B_v - partial_v B_u`.

The projective curvature is independently evaluated from centered derivatives
of the normalized state:

`Omega = 2 Im <D_u Psi | D_v Psi>`.

Wilson overlap products on the loop independently provide `Phi`. For a
shrinking square around a smooth point,

`Q_anti / area -> F_R`, `Phi_anti / area -> Omega`,

provided tick refinement suppresses the initialization remainder. Off center,
that remainder is `O(side/m)` while the loop signal is `O(side^2)`. The area
ladder therefore locks `m = round(0.96 / side^2)`, not a fixed `m` and not the
insufficient `m proportional to 1/side` exploratory scaling.

Where `Omega != 0`, the code records the local two-form quotient
`F_R / Omega`. In a two-dimensional parameter chart, any two nonzero 2-forms
are pointwise proportional, so this quotient exists algebraically. Requiring
the finite-loop quotient `Q_anti / Phi_anti` to approach `F_R / Omega` checks
the two separately computed area limits and their implementation; it has no
independent CGT-predictive content. The protocol also records that this
algebraic quotient varies across centers, so it cannot be treated as one
common/universal coefficient.

## Locked fixtures

- Derivative center: `(0, 0)`; derivative steps
  `0.004, 0.002, 0.001, 0.0005`.
- Fixed-side tick refinement: center `(0.18, 0)`, side `0.08`,
  `m = 48, 96, 192, 384`.
- Coupled area/tick refinement: center `(0, 0)`, sides
  `0.16, 0.08, 0.04, 0.02`, with `m = round(0.96 / side^2)`.
- Local quotient-consistency centers: `(0, 0)`, `(0.18, 0)`, `(0, 0.18)`,
  `(-0.18, 0.10)`; side `0.02`; `m = 2400`.
- Cyclic starts: center `(0.18, 0)`, side `0.08`, fractions
  `0, 1/4, 1/2, 3/4`, and `m = 96, 192, 384, 768`.
- Same-observable exact nulls: `current_phase_gain = 0` and
  `phase_relaxation = 1`, center `(0, 0)`, side `0.08`, `m = 96`.
- No seeds or pseudo-replicates are used; this is deterministic.
- No uncertainty interval is reported.
- A separate separable/zero-cross state map is excluded from this locked
  fixture; the two exact same-observable nulls test the implemented coupling
  without changing the observable or state family.

## Deterministic acceptance

The 12 compound clauses below map to 16 executable gates. The run passes only
if every executable gate passes:

1. Exact lag-recurrence residual is at most `5e-13`.
2. Every loop remains on unambiguous branch C0; increments and lags stay below
   `0.1` radians; every endpoint is duplicated.
3. Last-two response/projective derivative estimates change by at most `1e-4`
   relatively.
4. The legacy mean log-slope versus `m` is in `[-1.1, -0.9]`.
5. `|Q_anti - integral B|` has log-slope in `[-1.15, -0.8]`, and the finest
   relative error is at most `0.005`.
6. Coupled area/tick response-density errors decrease and finish at most
   `5e-4`; Wilson flux-density errors decrease and finish at most `2e-5`.
7. All finite-loop quotients approach the algebraic local `F_R / Omega`
   quotient within `0.005`, while the pointwise quotient spread is at least
   `0.15`. This is implementation consistency, not predictive evidence.
8. Both exact nulls have `max |q_t| <= 1e-14`.
9. Finest `|Q_even / Q_anti| <= 0.005`.
10. Cyclic-start spread scales with log-slope in `[-1.1, -0.9]` and ends below
    `0.007` relatively.
11. CCW/CW area signs reverse, `Phi_anti > 0`, and `Q_anti < 0` in the locked
    area fixture.
12. Tangent-line versus local-`F_R/Omega` Wilson quotient consistency is second
    order in side (relative-error slope in `[1.7, 2.3]`) and finishes below
    `2e-4`; this has no independent predictive content.

A finite value outside a threshold is a **fail**. A required ratio, slope, or
derivative that is undefined/non-finite is **indeterminate**, never a pass.
The CLI returns nonzero for either fail or indeterminate after writing all
artifacts.
