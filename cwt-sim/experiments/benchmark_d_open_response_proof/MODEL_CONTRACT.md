# Benchmark D open-response theorem specialization

## Status and claim ceiling

This document freezes an **internal analytic specialization** of the repository's authored
five-state Benchmark D open-system channel. It is not empirical evidence, external validation,
a physical-time or transported-charge result, a proof for the full scheduler, or support for a
CGT/readout alignment law. Numerical convergence checks exercise the implementation; they do not
replace the finite-dimensional contraction proof.

The experiment uses only:

- benchmark `benchmark_d`, fixed branch `D0`, with no continuation or branch switching;
- controls `(b,d)` on `b in [0.01,0.05]`, `d in [0.205,0.245]`, centered at `(0.03,0.225)`;
- `OpenSystemConfig(dt=0.18, edge_jump_scale=0.20, depolarizing=0.008,
  coherent_scale=0, site_potential_scale=0)` and dephasing `0.30`;
- the core geometry-blind Hermitian `mean_position=diag(1,2,3,4,5)` readout;
- the true affine fixed branch from a linear solve, never `stationary_from_row_stochastic` and
  never a finite-step `effective_branch_density` surrogate.

## Exact D0 kernel and core channel

Put `k_+=d+b` and `k_-=d-b`. The row-stochastic kernel is the reflecting five-site walk

```text
[1-k+   k+      0       0       0]
[ k-  1-k+-k-   k+      0       0]
[ 0      k-   1-k+-k-   k+      0]
[ 0       0      k-   1-k+-k-   k+]
[ 0       0       0      k-    1-k-]
```

The experiment-local expression is required to equal the named core D0 kernel pointwise. With
coherent and site-potential scales zero, the unitary is identity. The core jump probability scale
is

```text
q = dt * edge_jump_scale = 9/250.
```

The dephasing projectors and their contribution to the no-jump operator cancel exactly on the
invariant diagonal-density subspace. Consequently the population vector obeys the exact affine
update

```text
x_n = M(b_n,d_n) x_(n-1) + c,
M = (124/125) [(1-q) I + q K(b,d)]^T,
c = (1/625) 1.
```

The harness cross-checks this reduction against `cwt.cgt.open_system.apply_local_open_step`, the
core Kraus operators, the core observable, and the core iterative `fixed_point_density`. No core
API is modified.

## Smoothness, Kraus, rank, and contraction certificates

On the frozen box,

```text
k+ in [43/200,59/200],  k- in [31/200,47/200].
```

Thus the kernel clip at `[1/50,23/50]` is inactive with minimum margin `27/200`, and every authored
nonzero transition has support margin at least `31/200`. The largest Kraus sum term is
`1791/25000`; therefore the core `.98` rescale branch is inactive with margin `22709/25000`, and
the no-jump square-root radicand is at least `23209/25000`. Exact construction gives
`sum_a K_a^dagger K_a=I`.

For Hermitian trace-zero differences, the pre-depolarizing channel is CPTP and trace-norm
nonexpansive. Depolarization multiplies every difference by `124/125`, proving the uniform global
trace-norm contraction. On diagonal populations this is also a global `l1` contraction. The
depolarizing term supplies the exact global eigenvalue floor `1/625`. Setting depolarization to zero
must refuse this strict certificate rather than infer contraction from a sampled spectral estimate.
The reported five-by-five control mesh supplies only a sampled minimum eigenvalue and sampled
branch-variation diagnostic; it is not presented as the minimum over the continuous box.

The true branch is

```text
xbar(b,d) = [I-M(b,d)]^(-1)c.
```

Residual `epsilon` gives the Banach error bound `||x-xbar||_1 <= epsilon/(1-124/125)`. The harness
checks residual, trace, full rank, parameter variation, and that the core density projection changes
already-valid channel outputs only by floating-point roundoff.

## Centered response theorem and exact oracle

Let `H=(1,2,3,4,5)`, `X_i=partial_i xbar`, and let response be sampled only after the right-endpoint
update:

```text
r_n = H [x_n-xbar(b_n,d_n)],
Q = sum_(n=1)^N r_n,
B_i = -H (I-M)^(-1) M X_i.
```

The general repository proof program then specializes directly:

```text
Q = integral_gamma B + O(1/N)
```

for a fixed piecewise-smooth closed loop with equilibrium initialization. For exact reversed paths,
`Q_anti=(Q_CCW-Q_CW)/2` has the same limit. With the convention
`F_bd=partial_b B_d-partial_d B_b`, exact Fraction-valued implicit differentiation at the center
recomputes

```text
F_bd =
-1389405980846240823998759336989273383099794763750000000000
/
2559023550169319630994375590863181495045970285707766901
= -542.9438039967665...
```

The fraction is computed from the matrices and compared to the separately frozen formal oracle;
it is not accepted merely because the decimal was copied. An independent central-difference curl
and finite-loop line integrals provide implementation checks.

For a square of side `s`, the generic equilibrium-reset bound contains `O(s/N)`. Hence the
area-relative limit requires `N*s -> infinity`. Every registered shrinking square has side at most
`0.04`, so it remains in the certified box; the ladder doubles `N*s` at every level and checks
`Q_anti/s^2 -> F_bd`. A fixed-`N*s` ladder is explicitly not admissible. The `0.60` successive-error
ratio and `0.10` finest relative-error tolerances were selected during internal harness development
after this in-box ladder was chosen. They are deterministic numerical regression checks, not
preregistered evidence. The conservative solver-centering bound
`2 ||H||_infinity N e_fixed/s^2` is gated to be negligible relative to observed density error.

## Update, orientation, and endpoint conventions

The stored CCW square contains `4m+1` points: one initial point and one equal closing point. Each
segment join appears once. A cycle initializes at `xbar(lambda_0)`, skips sampling that duplicate
initial point, then performs exactly `4m` right-endpoint update/sample operations, including the
closing endpoint once. CW is the bytewise numerical reverse of the already-stored CCW array; it is
not regenerated from an orientation flag.

## Frozen controls and historical correction

The executable matrix includes:

- identity readout: zero orientation-odd response;
- constant fixed branch/channel: zero response one-form and orientation-odd response;
- depolarization zero: strict contraction certificate refused;
- Benchmark C C0: its true open-system fixed branch is `I/3` on the checked patch and its centered
  primary response is zero;
- the tracked Benchmark-C Phase10 configuration at recommended `gamma=0.2`: its recorded
  `effective_branch_density(branch_steps=2)` has a nonzero fixed residual and large distance from
  the true fixed branch;
- a separate Benchmark-D three-step diagnostic, explicitly not used to validate or reconstruct the
  tracked Benchmark-C Phase10 artifact.

The historical entry script `scripts/cgt/run_phase10_analysis.py`, the current recomputation
implementation `cwt/cgt/analysis/phase10_analysis.py`, and the tracked JSON bytes are each hash-bound
and labeled separately in provenance. The two Python identities use strict UTF-8/LF canonical bytes
that must equal their Git index blobs; the tracked JSON identity uses exact raw bytes that must equal
its Git index blob. The historical entry explicitly selected `branch_steps=2`;
the current library default is 3, so history is reproduced only by passing the recorded configuration
explicitly. The configuration-bound diagnostic does not prove the original run used the current
source checkout. Those historical numbers remain finite-step artifacts of their authored protocol;
they are not evidence against this true-fixed-branch response theorem.

## Constant projective-reference no-go control

The authored stationary-probability field of Benchmark D is not asserted to be a smooth projective
branch. Under the frozen zero coherent and site-potential scales, the channel is insensitive to the
declared `p` and `theta`. The harness therefore separately freezes the normalized constant state map

```text
p_j=1/5, theta_j=0, Psi_j=1/sqrt(5).
```

Its derivatives and `Omega_bd` are exactly zero, and its exact definition is hash-bound. This
constant state is channel-equivalent on the selected theorem path but is not the authored stationary
geometry. Nonzero response curvature alongside this exact-zero reference establishes only a
constant-reference no-go control: response curvature cannot, by itself, imply a universal CGT
alignment law.

## Fail-closed execution and source closure

Every C1-C10 disposition is derived from named executable gates. A failed gate changes its dependent
case disposition, makes the overall disposition `FAIL_INTERNAL_ANALYTIC`, and prevents artifact
writing; `run` and `verify` cannot print a passing disposition in that state. Provenance records a
sorted, path-bound set of local repository modules loaded by a fresh import of the same standalone
CLI entrypoint. It excludes import order, standard-library/site-package modules, bytecode, and cache
state, and rejects undeclared material local modules. The generic response theorem, this focused
test, and the tracked Phase10 generator/JSON are separately hash-bound dependencies.

## What does not follow

The separately declared constant reference has exact zero projective curvature while the centered
open-system response curvature is nonzero. This illustrates only the repository's no-go statement:
response curvature need not imply a universal alignment to an independently declared state
curvature. Nothing here establishes `F_R=kappa Omega`, a universal coefficient, topological
protection, physical pumping, empirical locality, or an external active-loop effect.
