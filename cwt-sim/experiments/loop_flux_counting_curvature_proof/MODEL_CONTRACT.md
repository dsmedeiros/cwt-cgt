# One-Chord Loop-Flux Counting-Curvature Model Contract

## Claim ceiling

This program may report only `PASS_INTERNAL_ANALYTIC`, `NO_EMPIRICAL_EVIDENCE`, and
`MODEL_SPECIFIC_RELATIONS_ONLY` for the exact experiment-local five-state model below. It does not prove
universal or full-CWT CWT/CGT alignment, calibrated physical pumping, empirical support, or a positive
general constitutive map.

The classification is:

`BOTH_CURVATURES_NONZERO / SCALAR_MAP_REFUTED_BY_SIGN_NONCOLLINEARITY /
GENERAL_GENERATOR_DEPENDENT_MAP_OPEN`.

This one inspected center is an analytic calibration/counterexample. It is not held out. The result refutes
only `SAME_CURVATURE` and a finite scalar relation `F = kappa Omega`. General linear, affine, nonlinear, and
generator-dependent response maps remain open.

## Frozen generator

The controls are `(b,d,t)` on

- `b in [1/100,1/20]`,
- `d in [41/200,49/200]`,
- `t in [1/3,2/3]`,

with center `(3/100,9/40,1/2)`. The fixed rates are path jump rate `a=1/5`, depolarizing reset
`delta=1/25`, site dephasing `gamma=3/10`, line coherent scale `h0=1/10`, zero site potential, and chord
radius `r=1/20`.

The D0 row-stochastic kernel supplies dissipative jumps only on the path. The Hamiltonian is

`H = d h0 sum_(j=0)^3 (|j><j+1|+h.c.) + z(t)|0><2|+z(t)^*|2><0|`,

where

`z(t)=r(1+i t)/(1-i t)=r[(1-t^2)+2 i t]/(1+t^2)`.

The column-stacked trace-linear generator is the exact Lindblad action plus
`delta(I Tr(rho)/5-rho)`. The affine reset source is never omitted. The theorem path does not use the core
linear-only `lindblad_superoperator`, Euler stepping, PSD projection, clipping, continuation, cached branch,
or any iterative stationary helper.

## Wilson flux and gauge

With `H[destination][source]`, the oriented cycle is `0->1->2->0`; its Wilson product is
`H10 H21 H02`. At the center,

- `z=(3+4i)/100`,
- `z_t=(-8+6i)/125`,
- `z_tt=(-16-88i)/625`,
- `H10 H21 H02=243/16000000+i 81/4000000`.

The reverse cycle is the complex conjugate. The diagonal-site gauge phases cancel around the Wilson product.
The raw chord phase is not itself presented as an invariant, and the core node-theta coboundary phase is
ineligible because it cannot create a nonzero loop flux.

The Cartesian quadratures `(x,y)=(Re z,Im z)` are the exact ambient algebra. The public three-control chart is
the rational Cayley coordinate `t`; at the center `d phi/dt=8/5`. Components with one `t` index equal `8/5`
times their phase-coordinate counterparts; the `bd` component is unchanged.

## Exact stationary branch and floor

The program solves `W p=0`, `Tr p=1` and the group inverse
`R=(W+p 1^T)^(-1)-p 1^T` exactly over Gaussian rationals. It checks `WR=RW=I-p1^T`, `Rp=0`, and
`1^T R=0`, then differentiates the stationary and Drazin equations through second order.

The uniform box certificate derives:

- minimum forward/reverse path rates `43/1000` and `31/1000`,
- induced-norm terms `49/500 + 1/10 + 98/125 + 3 = 1991/500`,
- cutoff `tau=1/40`, series parameter `1991/20000`,
- `exp(x)-1 <= x/(1-x)=1991/18009`,
- spectral displacement `1991/90045`,
- point floor `16018/90045 > 3/20`,
- stationary floor `2997/20000000`,
- trace-norm contraction `1/25` and Drazin bound `25`.

No producer-supplied floor or rank Boolean is acceptance authority.

## State geometry

Only the actual stationary state and its tangents enter the geometry lane. The SLDs solve

`X_i=(rho L_i+L_i rho)/2`.

The conventions are

- `g_ij=Tr[X_i L_j]=1/2 Tr[rho {L_i,L_j}]`,
- `Omega_ij=(1/(4i))Tr[rho[L_i,L_j]]`,
- vector order `(Omega_dt,Omega_tb,Omega_bd)`.

The exact tangent Gram and SLD metric determinants are positive. The center mean-Uhlmann vector has exact
signs `(-,+,-)` and nonauthoritative decimal regressions approximately
`(-3.735937244e-6,+1.153100439e-6,-1.287665364e-7)`.

## Counted response and FCS connection

Positive `q` counts the physical jump from zero-based node `1` to node `2`; the reverse jump has `-q`.
Only the two gain terms are tilted. At the center the forward/reverse rates are `51/1000` and `39/1000`.
With `J=partial_q W_q|0`, `j=1^T J`, and stationary tangents `X_i`,

`B_i=j R X_i`, and `F=dB`.

The exact center vectors have nonauthoritative decimal regressions

- `B=(.3166985595,-.00666512717,-.0000797604869)`,
- `F=(-.000286157594,-.00230897659,-1.00272082189)` in `(dt,tb,bd)` order.

An independent first-q left/right eigenvector jet proves the FCS connection identities
`B=-partial_q A|0` and `F=-partial_q dA|0`. This extended FCS eigenbundle connection is distinct from the
state mean-Uhlmann connection.

## Exact obstruction and open maps

`Omega_dt<0` and `F_dt<0` would require `kappa>0`; `Omega_tb>0` and `F_tb<0` would require
`kappa<0`. An exact nonzero cross-component minor separately proves noncollinearity. Therefore neither
`F=Omega` nor any finite scalar `F=kappa Omega` holds at the center.

A generic `3x3` map on two-form components is ineligible at one point. This program does not refute it,
an affine law, a nonlinear law, or a generator-dependent covariant tensor map. A future positive test must
predeclare the tensor law, use at least three independent calibration curvature vectors and preferably four or
more centers, enforce conditioning and nonzero gates, then predict a fresh uninspected rational center and
oblique bivector through a sealed response oracle. Count reversal and zero current must satisfy `K_-j=-K_j`
and `K_0=0`, and a varying map must satisfy its closure condition.

## Units, local scope, and nulls

`b,d,t,q` are dimensionless. `W` and `J` have inverse model-time units, `R` has model-time units, `B` is
count per control, `F` is count per control area, and `Omega` is dimensionless per control area. There is no
external clock or readout calibration.

Only local exact curvature `F=dB` at the reviewed center is claimed from exact branch jets. No third-jet
`dF=0` certificate, finite-time `O(1/T)` theorem, global Chern number, or graph-topology claim is made.

Reverse count is independently rebuilt and negates both `B` and `F` while leaving the state geometry and
Wilson loop unchanged. A zero current gives `B=F=0`. The outside-box `r=0` control removes the coherent
cycle, kills the `t` tangent/rank, and makes the `t` response components vanish. Chord conjugation is
recomputed on its actual stationary branch; only Wilson conjugation is assumed, not componentwise oddness.

## Fail-closed publication

Gates G0-G12, their case ownership, claims, and exact producer records are bound to independently frozen
digests. Geometry, counting, and oracle lanes have authenticated source closures and static import/call
firewalls. A criterion lock precedes the oracle, and the oracle capability contains no geometry, prediction,
orientation outcome, or fitted map coefficients.

The semantic source, documentation, and focused-test closure is authorized only by `SOURCE_LOCK.json` with
schema `git_index_source_lock_v1`. That lock is built from explicitly resolved Git index entries and
`cat-file` blob bytes with replacement-object rewriting disabled. At the source-lock generation boundary,
the full selected-index delta against the reviewed parent must be exactly the 16 new proof paths; the two
reviewed tracked dependencies remain byte-identical, giving 18 semantic entries total and permitting no
lock, artifact, unrelated, deletion, rename, or mode delta. A separate precommit publication audit requires
exactly those 16 sources plus `SOURCE_LOCK.json` and the five artifacts, for 22 additions. Normal runtime
verification does not remain tied to that old-parent global delta: it validates the exact 18 semantic index
entries, lock, and worktree bytes, so later nonsemantic repository additions cannot permanently disable the
proof verifier. The lock records exact `100644` modes, blob OIDs, sizes, raw SHA-256 values, and ordered
path/entry digests. The lock and generated artifacts are excluded from the semantic source inventory. A
copied checkout without explicit Git directory, index, and worktree binding has no worktree-hash fallback.
Authoritative provenance acceptance is an outer staged-index audit followed by a fresh operating-system
process from an exact index-materialized private checkout. The checkout has no `.git`; the process receives
explicit absolute `GIT_DIR`, `GIT_INDEX_FILE`, and `GIT_WORK_TREE` bindings, runs a trusted absolute Python
executable with `-I` and user-site disabled, and uses a trusted absolute Git executable with replacement
objects disabled. It runs the fixed `source_lock.py verify-json` entrypoint and, after artifact generation,
the standalone `run.py verify` CLI. Both must succeed before publication.

Library helpers also parse/recompute the disk lock and replay the index-extracted verifier as useful
defense-in-depth diagnostics. They are not the publication authority and do not claim resistance after
arbitrary mutation of the current process memory, syscall wrappers, interpreter or Git binaries, or
administrator-controlled execution state. The outer clean-process staged audit, not `_verified_source_lock`,
is the authority boundary.

The five canonical artifacts are strict UTF-8/LF, Git-index-source/predecessor closed,
dependency-policy bound, and published by a local crash-safe cooperating-reader transaction. Provenance
records the raw source-lock SHA-256 and its source-bundle digest. `run`, `status`, and `verify` all require the
same semantic recomputation. Any failed gate, forged record, source/index/lock drift, provenance drift, or
artifact drift must refuse PASS and publication.
