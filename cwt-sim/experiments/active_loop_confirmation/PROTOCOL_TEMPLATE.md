# Active-loop confirmation protocol template (design only)

Version: `active-loop-confirmation-v2`
Current state: **`BLOCKED_NO_SUBSTRATE`**
Evidence status: **none**

> This file is a reusable design template, not a study preregistration, not a
> frozen substrate protocol, and not empirical or theoretical evidence. No
> substrate is named or qualified; all source-specific fields, power results,
> smallest effect of interest (SESOI), numerical margins, and remainder
> constants remain null. The colocated package has no outcome loader, response
> reducer, confirmation command, or raw-data access path.

The template is intended to prevent a future active-loop study from repeating
the circular response construction, fixed-tick ambiguity, pseudoreplication,
and post-outcome threshold selection found in earlier exploratory work. A
source-specific protocol may be frozen only after every item below has a
reviewable, immutable value and independent preflight approval.

## G0 — status and implementation ceiling

1. The checked-in state is `BLOCKED_NO_SUBSTRATE`.
2. The metadata validator can reach at most
   `METADATA_VERIFIED_PENDING_IMPLEMENTATION`; it cannot emit a study `PASS` or
   `FAIL` and cannot execute an outcome.
3. No production or confirmation loader may exist until every substrate field
   is non-null, the source passes G1, and the prepared metadata has been
   independently reviewed.
4. A future execution vocabulary must distinguish `BLOCKED` (no eligible or
   complete design), `INDETERMINATE` (execution/integrity failure), `FAIL`
   (valid finite miss), and `PASS` (every conjunctive gate met). The current
   tool emits only metadata states.
5. Passive, simulated, model-generated, derived-only, or natural-cycle inputs
   are ineligible for the active confirmation even if they are external.

## G1 — immutable active physical source

The future primary source must supply immutable primary raw physical
measurements from an actually executed intervention. The manifest must bind,
with separate fields rather than one aggregate `external=true` flag:

- physical device/specimen and session/block identifiers;
- randomized and counterbalanced loop orientation assignments;
- raw commanded and raw achieved control logs;
- a raw response sensor independent of the geometry/state sensor;
- physical timestamps, units, resets, washouts, and block boundaries;
- revision, license, per-file byte hashes, and a manifest hash; and
- source diagrams and enough hardware/procedure metadata to audit the exact
  zero-coupling intervention.

Field-observation status, externality, and physical intervention are different
claims and must be established independently. A fixture or synthetic example
cannot qualify a future study or a test fixture for `PASS`.

## G2 — coordinates, sign convention, and factor conventions

There must be at least three independently actuable controls. Freeze each under
a canonical structured identifier of at least five characters (for example
`field_x`), together with its physical units, reference value, scale, and
ordered right-handed basis before opening response outcomes. Use normalized coordinates

\[
x^i=\frac{\lambda^i-\lambda^i_{\mathrm{ref}}}{L_i},\qquad d\ge 3.
\]

The repository convention is

\[
\mathcal A_i=-i\langle\Psi|\partial_i\Psi\rangle,\qquad
\Omega_{ij}=+2\,\operatorname{Im}C_{ij},\qquad
\Omega=\frac12\Omega_{ij}\,dx^i\wedge dx^j.
\]

For an oriented spanning surface, the exact finite-loop flux is

\[
A^{ij}=\int_S dx^i\wedge dx^j,
\qquad
\Phi(S)=\int_S\Omega
=\frac12\int_S\Omega_{ij}(x)\,dx^i\wedge dx^j.
\]

In exactly three coordinates define

\[
\boldsymbol\omega=(\Omega_{23},\Omega_{31},\Omega_{12}),\qquad
\mathbf a=(A^{23},A^{31},A^{12}).
\]

For constant curvature, or with `omega` defined as the exact area-averaged
curvature, `Phi=omega.a`. For a shrinking loop centered at `c`, the local
approximation is `Phi=omega(c).a+O(s^3)`, not an exact finite-surface identity.
The frozen predictor must use integrated-curvature or Wilson flux; any local
`O(s^3)` approximation enters the G9 remainder rather than being silently
absorbed into `Phi`.

Positive boundary orientation follows the right-hand rule of the frozen basis.
The negative traversal must be the pointwise time reverse
`gamma_minus(t)=gamma_plus(T-t)`, not a separately generated nominal loop.

## G3 — response firewall and physical-time integral

The response reducer is written and byte-hashed before treatment labels are
joined. Its complete input schema is restricted to:

1. a pseudonymous episode/window ID matching the frozen
   `ep_[0-9a-f]{16}` SHA-prefix form;
2. physical timestamps;
3. calibrated raw response `Y(t)`;
4. a predeclared response-only baseline `b(t)`; and
5. response-sensor QC.

It may not receive control values or paths, path order, coupling labels,
orientation, area or area vector, `Phi`, `Omega`, the geometry state, or any
fitted coefficient. Filenames and IDs may not proxy those fields. The firewall
derives aliases from every canonical control/right-handed identifier (including
underscore, dash, and compact forms) and rejects those aliases, plus
separator-insensitive compact `cw`, `ccw`, `clockwise`, `counterclockwise`,
`positive`, `negative`, `zero`, and whole-token-only `on`, from response-side signal, baseline, units, IDs, weights,
model descriptions, geometry-contrast descriptions, and raw manifest paths.
The reducer locks

\[
Q=\int_0^T [Y(t)-b(t)]\,dt
\]

using the exact timestamp-weighted trapezoidal physical-time rule
`timestamp_weighted_trapezoidal_Q_integral_v1`. Timestamps are seconds. Units
are `[Y] * time`, and the signal, signal units, integrated `Q` units, and their
units derivation are frozen separately; tick/sample/cycle pseudo-units are
forbidden. `Q` must
not be called charge unless `Y` is a calibrated electrical current and the
resulting units are charge. Deleting or mutating all geometry metadata must
leave serialized `Q` bytes identical. That mutation test is a hard preflight
gate.

## G4 — complete quartet and primary interaction estimand

Within every independently randomized, reset/washout block `b` and loop `l`,
execute the complete balanced quartet

\[
\{\text{coupling on},\text{coupling zero}\}
\times\{\text{positive},\text{negative orientation}\}.
\]

For `c` in `{on, zero}` define

\[
Q_{\mathrm{anti},c}=\frac{Q_{c,+}-Q_{c,-}}2,
\]

and the primary interaction

\[
D_{bl}=Q_{\mathrm{anti,on}}-Q_{\mathrm{anti,zero}}
=\frac12\left[(Q_{\mathrm{on},+}-Q_{\mathrm{on},-})
 -(Q_{0,+}-Q_{0,-})\right].
\]

The ordinary difference-in-differences contrast is **`2 D_bl`**. Reports must
not silently interchange `D`, `2D`, a single oriented traversal, or a full
forward-minus-reverse difference.

The frozen statistical and randomization unit is exactly an
`independently_randomized_washed_out_reset_block`: a genuine physical
device/specimen or an independently randomized, fully washed-out reset. Ticks,
samples, sensors, loops on the same unreset device, and RNG seeds are not
independent units.

## G5 — physical clock and achieved paths

Freeze a physical-time family

\[
\lambda(t)=c+sLz_h(t/T),\qquad 0\le t\le T,
\]

including waveform, seconds `T`, physical `dt`, endpoints, quadrature,
latency/jitter bounds, washout or periodic initialization, commanded path,
achieved path source, and closure tolerance. A `dt` ladder holds `T` and the
geometry fixed; a `T` ladder holds geometry fixed; an `s` ladder holds the
declared adiabatic `T` rule fixed. A discrete relaxation must declare a physical
map `alpha(dt)=1-exp(-dt/tau)` with finite positive physical `tau`; the typed
map must declare `fixed_alpha_across_dt_ladder=false`. Fixed `alpha` while
increasing the number of ticks is not fixed physical time and is ineligible.

The achieved path, not merely the command, supplies realized geometry after
predeclared path QC. Missing physical units, a tick sum, unbounded clock error,
or missing achieved-path closure is `INDETERMINATE` in a future run.

## G6 — cluster split and loop rank

Before response outcomes are opened, assign whole dependent clusters to
`calibration`, `reduction_validation`, and `confirmation` with a published salt
and metadata-only hash. Cluster at the physical site/device/session/block level.
Reject aliases and duplicate content across partitions; siblings, resets, or
windows from the same dependent unit may not leak.

Confirmation centers, at least one `C2` loop shape, and tensor directions stay
unopened. At every confirmation center, the area-vector design must have rank
three with a frozen condition-number limit. Normalize exactly three nonzero
area vectors to unit Euclidean norm, form the 3-by-3 row matrix `A`, and compute
`||A||_F ||A^{-1}||_F`; the declared value must reproduce and not exceed the
frozen threshold. A held-out direction must satisfy a frozen maximum absolute
cosine below one against every primary normal, so an axis repeat is forbidden.
Freeze the achieved, not only planned,
area-vector rule. The study needs at least 20 independent blocks. The number of
confirmation clusters must be at least `max(20, N_powered)`, where `N_powered`
is frozen from the calibration-cluster power calculation. That calculation
must reach at least 0.90 separately for every conjunctive primary gate, with an
explicit effect, variance, method, assumptions, seed, and independent-unit
count. These source-specific quantities are currently null.

## G7 — geometry firewall

The geometry state/sensor must be distinct from `Y` and its baseline. Freeze
the state map, branch rule, projector, Wilson-loop and derivative-QGT
estimators, code hashes, derivative/settling checks, gap isolation, overlap,
and gauge checks before response unlock. Geometry may receive state and control
data but never `Y`, `b`, or `Q`. The prediction uses planned geometry or
pre-unblinding achieved-path `Phi` under a locked choice; it cannot choose
between them after observing response.

Because the primary response is the on-minus-zero interaction `D`, its geometry
predictor must also be frozen before response unlock. A common/on-state `Omega`
or `Phi` is admissible only if the zero intervention is shown, within frozen
positive state, achieved-path, and curvature-equivalence margins, to sever only
the state-to-readout coupling while leaving the state map and geometry
equivalent. If zero coupling changes geometry, the predictor must instead use a
predeclared geometry-interaction contrast with its own code hash. The two modes
cannot be selected after response inspection.

## G8 — nondegeneracy and exact mechanism control

The zero-coupling condition must physically sever the proposed
state-to-readout path while retaining the same schedule, sensors, processing,
and nuisance hysteresis. Use the identical response reducer. A reference
injection into the response sensor must establish dynamic range and absence of
saturation. A valid zero-control or zero-flux orientation effect is a mechanism
`FAIL`, not an exclusion. Likewise, nonzero geometry with zero response is an
allowed substantive null.

## G9 — tangent reduction, Stokes check, and remainder

Because `D` is an on-minus-zero interaction, the relevant tangent one-form and
curvature are

\[
B^D=B^{\mathrm{on}}-B^0,\qquad F_R^D=dB^D.
\]

Do not compare `D` to on-only `F_R` unless `B^0=0` has been independently
proved. Derive or estimate the tangent response without `Omega`, for example

\[
Y-Y_{\mathrm{eq}}=B_i\dot x^i+O(|\dot x|^2),
\]

or supply the correct memory-kernel limit. The source must select exactly one
asymptotic regime through the machine enums, bind the same structured
initialization and regularity modes in the physical-time section, and freeze a
hashed common-norm definition plus uniform contraction bound `rho<1`. A hashed
derivation certificate must be theory/calibration-only, locked before
confirmation, and explicitly attest that it used neither confirmation data nor
outcome response. The tangent derivation, fixed norm, selected domain, and six
validation checks are represented only by recursively closed hash-bound
definition records: exact definition ID, one fixed neutral relative artifact path,
SHA-256, `theory_only` or `calibration_only` stage, fixed provenance, pre-lock
flag, and a false confirmation/outcome-use flag. Inline descriptions are not
accepted. Current metadata validation checks only this closed record shape,
the exact ID/path declarations, SHA-256 syntax, and the record's own flags. It
does **not** resolve the paths, establish that files exist, recompute their
hashes, authenticate content, or prove the mathematics. The checked template
therefore keeps `reference_content_authentication` explicitly unimplemented
and forbids implementation or response unlock. A future reviewed
implementation must resolve every reference within one frozen root, verify
containment, existence, regular-file type, and raw-byte SHA-256, and include
the bytes in the immutable closure before either implementation or response
unlock. Independent semantic review of every resolved record is additionally
required.

For an equilibrium reset, the generic discrete theorem retains its endpoint
boundary term:

```text
|r_discrete| <= C_N1*s/N + C_N2*s^2/N,
discrete area-relative limit: N*s -> infinity.
```

The corresponding generic stable-ODE remainder and area-relative limit are

```text
|r_continuous| <= C_T1*s*tau/T,
continuous area-relative limit: s*T/tau -> infinity.
```

The stronger regime is separately admissible only under one of two exact
structured contracts: `unique_driven_periodic_orbit` paired with
`periodic_c3_endpoint_consistent_full_period`, or `matched_c3_corrector` paired
with `endpoint_flat_c3_matched_corrector`. The corresponding typed certificate
must be `periodic_summation_by_parts_v1` or
`endpoint_flat_matched_corrector_v1`, respectively, and must carry a non-null
SHA-256 for the cancellation proof. Equilibrium reset, `C2`, free-text
self-attestation, or a missing cancellation hash cannot claim the improved
rate:

```text
|r_discrete| <= C_N1*s^2/N + C_N2*s/N^2,
discrete area-relative limits: N -> infinity and N^2*s -> infinity;
|r_continuous| <= C_T1*s^2*tau/T + C_T2*s*(tau/T)^2,
continuous area-relative limits: T/tau -> infinity and s*(T/tau)^2 -> infinity.
```

The locked total deterministic bounds add the declared finite-sampling term
and local-flux approximation term. For the generic regime this is

```text
|r| <= C_N1*s/N + C_N2*s^2/N + C_T1*s*tau/T
       + C_dt*s*(dt/tau)^p + C_phi*s^3,
```

and for the improved regime it is

```text
|r| <= C_N1*s^2/N + C_N2*s/N^2 + C_T1*s^2*tau/T
       + C_T2*s*(tau/T)^2 + C_dt*s^2*(dt/tau)^p + C_phi*s^3.
```

A rigorous stochastic analogue must give an explicit probability statement.
Here `s`, `tau/T`, and `dt/tau` are dimensionless, `p>0`, and every `C` has the
integrated-`Q` units of `D`. The machine lock requires exact equality between
those units, the SESOI units, and the interaction-nondegeneracy units. The
selected control/time domain and deterministic or stochastic interpretation
must be frozen. `C_phi*s^3` is retained when the local `O(s^3)` vector-area flux
approximation is used and may vanish only when exact integrated/Wilson flux is
used. Every constant that appears in the selected bound is strictly positive;
the unused `C_T2` is exactly zero in the generic regime. An equilibrium-reset
source cannot claim either improved rate.
Use at least four fit levels plus a held-out level for each of the `s`, `T`, and
`dt` ladders. Predeclare reversal, cyclic start, smooth reparameterization,
concatenation, matched-area shape, and `D`-versus-`\oint B^D` checks. A valid
bound/test miss is `FAIL`; an execution, branch, QC, or undefined-estimator
defect is `INDETERMINATE`.

## G10 — non-tautological three-dimensional CGT prediction

In three coordinates define the response-curvature vector

\[
\mathbf f_R^D=(F^D_{R,23},F^D_{R,31},F^D_{R,12}).
\]

Freeze one constant or low-dimensional calibration-only model as a typed,
hashed record whose fit partition is exactly `calibration`, whose confirmation-
response and held-out local response/curvature-ratio flags are false, and whose
description is defensively proxy-scanned:

\[
\mathbf f_R^D(c)=\kappa(z_c)\boldsymbol\omega(c)+\boldsymbol\epsilon(c).
\]

Weights likewise use a typed `calibration_design_only_v1` provenance record,
false confirmation/held-out response flags, and a pre-unlock SHA-256. A geometry
interaction uses a typed state-only contrast with response inputs forbidden and
its definition/code hashes frozen. The spellings `held-out`, `held_out`,
`held out`, `heldout`, and the corresponding `hold*` forms are canonicalized to
the same forbidden marker; `confirmation` is likewise forbidden in these three
free-text provenance fields, regardless of neighboring text or Unicode. The
typed fields are the sole provenance authority, with no prose exception. Unlike the pointwise quotient of two 2-forms in two dimensions, vector
collinearity across a full-rank three-dimensional area design is not an
algebraic identity. Never divide held-out `F_R` by held-out `Omega`; never fit
on confirmation centers, tensor directions, or responses. Before confirmation
`Y` is unlocked, hash

\[
\mu_l=\widehat\kappa(z_l)\Phi_l.
\]

`Phi_l` is the exact integrated/Wilson flux from G2/G7. If common/on geometry is
frozen, the G7 equivalence gates must pass. Otherwise the formula must use the
predeclared geometry-interaction predictor rather than an unspecified on-only
`Phi`.

Propagate both calibration-model and geometry uncertainty into prediction
magnitude and coverage. Freeze a full-rank/condition threshold, an oblique
held-out direction, and the treatment of near-zero `Omega`. The orientation
randomization test may condition on the already hashed `mu_l`.

## G11 — inference and conjunctive decision

With predeclared nonnegative calibration/design-only weights, whose formula and
table hash are frozen before confirmation response access, define the primary
statistic `T:=S` by

\[
S=\sum_{bl}w_l\mu_lD_{bl},\qquad
\widehat\beta=\frac{\sum_{bl}w_l\mu_lD_{bl}}
 {\sum_{bl}w_l\mu_l^2}.
\]

The sharp randomization null `H0` states that the locked response outcomes are
invariant under every admissible balanced quartet orientation-label assignment
within each frozen independent-block stratum. The one-sided alternative `H1`
is a larger positive `T` in the already hashed CGT-predicted direction. The
randomization group `G` consists exactly of all distinct balanced block-level
quartet sign-code assignments within frozen strata. These assignments preserve
the on/zero quartet pairing and frozen balance constraints; labels never move
across strata. Replay the actual
assignment, never tick, sensor, loop-row, or window labels. Count ties as
extreme (`T_perm >= T_obs`), deduplicate assignments, and include the observed
assignment exactly once.

If the complete admissible group is enumerated, let
`K=#{g in G:T_g>=T_obs}` and report exactly `p=K/|G|`; there is no Monte Carlo
interval; `p<0.01` passes and `p>=0.01` fails that exact-enumeration gate.
Otherwise draw exactly `M=999999` assignments independently and uniformly with
replacement from `G` under the frozen seed and report

\[
p=\frac{1+K}{M+1}.
\]

Only the sampled branch reports a 99% Clopper-Pearson interval for the
permutation-tail probability `q=P(T_perm>=T_obs)`. At `alpha=0.01`, its upper
bound below 0.01 passes the randomization gate, its lower bound above 0.01
fails, and a straddle is `INDETERMINATE`; there is no extension or branch
switch after seeing the interval.

Before confirmation, freeze a physical-response SESOI `delta_Q`, a beta
equivalence margin `epsilon_beta`, a perpendicular/tensor margin
`epsilon_perp`, and a comparator loss advantage `delta_L`. These are
source-specific and remain null in this template. `PASS` requires all of:

- firewall, source, clock, quartet, split, geometry, and estimator validity;
- the randomization gate;
- the 99% beta interval inside `[1-epsilon_beta,1+epsilon_beta]` and a response
  lower bound above the physical SESOI;
- a 99% upper bound on the perpendicular ratio below `epsilon_perp`;
- CGT prediction loss beating one locked strongest non-CGT
  antisymmetric/hysteresis comparator by `delta_L`, using the locked
  dimensionless normalized prediction loss and independent-block aggregation;
- a nondegenerate on-versus-zero interaction; and
- every tangent/remainder and control gate.

A finite valid miss is `FAIL`. Undefined rank, gap, leakage, unregistered
exclusion, QC failure, underpower, or Monte Carlo straddle is `INDETERMINATE`.
Secondary tests use Holm correction at 0.05 and cannot rescue a primary miss.
Sample size is fixed; there is no interim look or top-up.

The source-specific freeze must supply complete formulas rather than bare
margin names. It must define: the cluster-valid 99% interval for `beta_hat`,
including calibration-model and geometry uncertainty; the response lower-bound
target and its relation to `delta_Q`; the perpendicular component and ratio,
including a frozen denominator floor and near-zero rule; the strongest locked
non-CGT comparator, prediction loss, aggregation unit, and uncertainty method;
and the confidence-bound rule for a nondegenerate `D` interaction. Each object
must say which finite miss is `FAIL` and which undefined denominator, rank,
coverage, or QC state is `INDETERMINATE`. Power must be at least 0.90 for every
one of these conjunctive gates, not merely for an omnibus statistic.

## G12 — controls, lock, recovery, and claim ceiling

Required controls are: a retraced zero-area sham; an `Omega`-orthogonal
nonzero-area loop; order counterbalancing; gauge invariance; component and
center scrambles; a response-sensor reference injection; and zero, metric-only,
control-only, and strongest non-CGT antisymmetric/hysteresis comparators.

A source-specific lock must close over raw lineage, units, apparatus diagrams,
cluster split, waveform/randomization table, command and achieved paths,
QC/missingness rules, code/container/dependencies, seeds, predictions, and
every byte hash through an acyclic manifest. Verify from a clean index/archive
and checkouts with platform line-ending settings before authorization.

There is one authorized confirmation execution. A recovery is allowed only
under a pre-frozen rule requiring: no result, stdout outcome, or statistic was
observed; no process or partial result artifact remains; every input digest is
identical; a durable incident ledger exists; and an independent reviewer
reauthorizes the identical replay. Otherwise the study is `INDETERMINATE`.

Even a future `PASS` is limited to the named substrate, control region, branch,
coupling, readout, time regime, and loop family. It cannot establish universal
CWT/CGT, topology or topological protection, passive ridges, strict locality,
population generalization, or transported charge without the required units.

## Current template disposition

No qualifying substrate is asserted. The machine template deliberately leaves
all source identity, qualification, coordinate realization, clock, response,
power, SESOI, margins, and validation thresholds null. Therefore:

- current state: `BLOCKED_NO_SUBSTRATE`;
- outcome execution: unavailable by design;
- confirmation result directory: absent by design;
- evidence contribution: none; and
- next permissible action: identify a candidate source and perform a
  metadata-only qualification review without accessing response outcomes.

The non-exhaustive metadata review in `SUBSTRATE_SCREEN.md` records current
near-misses and a preliminary prospective collection outline. It does not
qualify a substrate or alter this disposition.
