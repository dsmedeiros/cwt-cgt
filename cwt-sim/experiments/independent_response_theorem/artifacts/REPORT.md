# Geometry-blind-response discrete theorem report

> **Evidence tier:** internal synthetic/analytic benchmark-C fixture. This is not external evidence, a preregistration, an untouched holdout, transported charge, or a physical-pump validation.

> **Terminology:** the experiment directory's "independent response" means only that response is calculated without geometry/orientation inputs. It is not independent empirical validation.

**Scoped outcome:** `PASS` for the explicit fixed-tick theorem.  
**Central empirical/external CWT claim:** `PROOF INCOMPLETE`.

The `discrete_cycle_sum_surrogate` and numerical acceptance thresholds were selected after an exploratory center-`(0, 0)` square refinement probe. All configurations here are discovery/analytic fixtures. The legacy mean `response` is unchanged.

## Fixed semantics

`dt=1`; `phase_relaxation=0.35` per current tick. Increasing steps lengthens and slows the cycle. `Q=sum(q_t)` has circulation-current-tick units. The explicitly duplicated closing endpoint is processed.

The response calculator receives branch states/path, relaxation, and current gain only. Signed area, orientation metadata, curvature, and Wilson flux are computed separately afterward.

## Numerical result

| Quantity | Value |
|---|---:|
| `F_R` at `(0,0)` | -0.0793510689616 |
| `Omega` at `(0,0)` | 0.145833318196 |
| algebraic local two-form quotient `F_R/Omega` | -0.544121672218 |
| legacy mean log-slope | -1.01045767 |
| summed tangent-remainder log-slope | -0.957944817 |
| finest `Q_anti/A` relative error | 0.000247391322 |
| finest `Phi_anti/A` relative error | 2.12883954e-06 |
| max finite-loop/local quotient consistency error | 0.00301188363 |
| local two-form quotient spread | 0.392932077 |
| max exact-null `|q_t|` | 7.63278329e-17 |
| finest `|Q_even/Q_anti|` | 0.00014080265 |

In a 2D parameter chart, any two nonzero 2-forms are pointwise proportional. Thus `F_R/Omega` versus `Q_anti/Phi_anti` is only an algebraic quotient/implementation-consistency check and has no independent CGT-predictive content. The quotient also varies across centers, so it is not one common or universal coefficient.

## Deterministic gates

The protocol's 12 compound acceptance clauses map to the 16 executable gates below.

| Gate | Status | Requirement |
|---|---|---|
| `exact_lag_recurrence` | **PASS** | max wrapped recurrence residual <= 5e-13 |
| `fixed_branch_no_wrap_domain` | **PASS** | C0 only, no ambiguous steps, and phase increments/lags < 0.1 rad |
| `endpoint_duplication` | **PASS** | every loop includes the legacy duplicated endpoint |
| `tangent_derivative_stability` | **PASS** | last-two central-difference relative changes <= 1e-4 |
| `legacy_mean_vanishes_with_ticks` | **PASS** | log slope versus steps lies in [-1.1, -0.9] |
| `summed_remainder_is_inverse_tick` | **PASS** | |Q_anti-line integral| log slope lies in [-1.15, -0.8] |
| `discrete_cycle_sum_converges_to_tangent_line` | **PASS** | finest fixed-side relative error <= 0.005 |
| `coupled_area_tick_response_limit` | **PASS** | m scales as 0.96/side^2; errors decrease and final error <= 5e-4 |
| `wilson_flux_density_limit` | **PASS** | Wilson Phi_anti/area errors decrease and final error <= 2e-5 |
| `two_dimensional_quotient_consistency` | **PASS** | finite-loop Q_anti/Phi_anti approaches pointwise F_R/Omega within 0.5%; this is an algebraic 2D quotient consistency check, not predictive evidence |
| `local_two_form_quotient_is_not_common` | **PASS** | pointwise F_R/Omega quotient spread >= 0.15; no common coefficient is inferred |
| `same_observable_exact_nulls` | **PASS** | gain=0 and phase_relaxation=1 each give max |q_t| <= 1e-14 |
| `orientation_even_contamination` | **PASS** | |Q_even/Q_anti| <= 0.005 on the finest coupled refinement |
| `cyclic_start_remainder` | **PASS** | start-point spread scales as 1/m and final relative spread <= 0.007 |
| `orientation_and_area_signs` | **PASS** | CCW/CW areas reverse, Phi_anti > 0, and Q_anti < 0 |
| `two_dimensional_quotient_spatial_convergence` | **PASS** | line-vs-local-(F_R/Omega)*Phi consistency error is second order and final <= 2e-4; this has no independent predictive content |

No seeds, replicate inflation, confidence intervals, or pseudo-statistical claims are used. See [`PROTOCOL_LOCK.md`](../PROTOCOL_LOCK.md), `records.json`, `summary.json`, and `PROVENANCE.json` for formulas, raw deterministic records, gates, tracked source hashes, and canonical summary/records payload hashes.

## External-data blocker

No auditable raw paired-loop dataset, frozen manifest/checksum, and independent measured response are tracked and runnable in this repository.
A future central-claim test still needs a frozen manifest/checksum, auditable raw paired loops, an independent response that never receives geometry/orientation, and a held-out analysis plan.
