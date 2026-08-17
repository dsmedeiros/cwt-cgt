# Curvature identity audit — frozen analytic contract

## Status and scope

This package is an internal analytic audit of when a response curvature and a
CGT/QGT projective curvature can be identified. Its maximum disposition is
`PASS_INTERNAL_ANALYTIC / NO_EMPIRICAL_EVIDENCE`. It does not establish a
universal CWT law, a physical response, a finite-speed pump, a general
CGT-response alignment, or empirical evidence.

All three executable examples are authored repository models. Numerical
eigensystem, finite-difference, and Wilson-loop evaluations are implementation
regressions only; they do not supply the analytic acceptance argument.

## Common-origin theorem

Let `sigma: Lambda -> N` be one frozen smooth branch graph, let
`P: N -> CP^(n-1)` be its projective map, let `beta_R` be a response one-form
on `N`, and let `omega_FS` be the Fubini–Study two-form. Define the pulled-back
response one-form and local pulled-back Berry connection by

```text
B_R      = sigma^* beta_R,
A_Lambda = sigma^* P^* a_B,       d a_B = omega_FS on a gauge patch,
F_R      = d B_R = sigma^*(d beta_R),
Omega    = d A_Lambda = sigma^*(P^* omega_FS).
```

Type `kappa` as a smooth real scalar on `Lambda`. The necessary and sufficient
branch-tangent condition is exactly

```text
sigma^*(d beta_R) - kappa sigma^*(P^* omega_FS) = 0.
```

Equivalently, the parenthesized two-form must vanish on every pair
`d sigma(v), d sigma(w)` for `v,w in T Lambda`. Ambient equality away from the
branch is neither necessary nor asserted.

For constant `kappa`, equality is equivalent to the closedness condition

```text
d(B_R - kappa A_Lambda) = 0.
```

Only on a contractible branch chart does closedness imply
`B_R-kappa A_Lambda=d chi`. This statement does not carry over unchanged to
variable `kappa`, because `d(B_R-kappa A_Lambda)` also contains
`-d kappa wedge A_Lambda`. On a noncontractible chart, every period of the
pulled-back form `B_R-kappa A_Lambda` must also vanish. Globally, nonzero
pulled-back Chern flux forbids one smooth `A_Lambda`. If `B_R` is global and
`kappa` is a nonzero constant, the zero integral of `dB_R` over a closed
surface conflicts with a nonzero `kappa integral Omega`.

Pointwise `F/Omega` fitting, a two-dimensional quotient presented as a
prediction, an unfrozen tensor map, an auxiliary state substitution, and any
limit-to-ontology upgrade are rejected. A future positive CWT alignment test
must use at least three full-rank area directions, freeze its tensor map before
response access, and predict a held-out oblique direction without pointwise
division. This package does not instantiate that future test.

## QP-1 — same-curvature calibration only

The same Hermitian operator `H=qp1_builder(x,y)` supplies both its dominant
projector and the perturbations. In the north gauge,

```text
psi = (cos(pi y/2), exp(i 2 pi x) sin(pi y/2)),
A_x = 2 pi sin^2(pi y/2),       A_y = 0,
Omega_xy = -pi^2 sin(pi y).
```

The gap is `2/5+(1/5)cos(2 pi y)` and lies in `[1/5,3/5]`. Differentiating the
eigenproblem gives

```text
<u1|partial_i u0> = <u1|partial_i H|u0> / (mu0-mu1).
```

For

```text
K_ij[O] = 2 Im <u0|O_i|u1><u1|partial_j H|u0> / gap^2,
```

the independently declared `O_i=+partial_i H` yields
`(K_xy-K_yx)/2=+Omega_xy`. The conventional generalized force
`O_i=-partial_i H` yields `-Omega_xy`. Full antisymmetrization is exactly twice
the half-antisymmetrized coefficient.

The south gauge satisfies `psi_S=exp(-i2pi x)psi_N` and
`A_S=A_N-2pi dx`. The total curvature is `-2pi`, the Chern number is `-1`, and
no global smooth connection exists. This is a same-operator sign/factor
calibration, not a finite-speed response or live CWT result.

## Benchmark C — same primitive manifold, different connections

On the interior C0 patch, freeze

```text
z = (17u/20+v/2, -7u/10+7uv/20, -11v/20-uv/4),
p_j = exp(z_j) / sum_k exp(z_k),
phi = 7v/10+9uv/20+3u/20,
theta = (phi,0,-phi),
k_plus = 9/50+u/10,       k_minus = 9/50-u/10,
alpha = 7/20,              gain = 9/20.
```

Both forms pull back along the same graph `lambda -> (p,theta,K)`, but from
different connections:

```text
A_i = sum_a p_a partial_i theta_a,
Omega_uv = sum_a[(partial_u p_a)(partial_v theta_a)
                 -(partial_v p_a)(partial_u theta_a)],

H_a = partial J(p,x,K;gain)/partial x_a evaluated at x=theta,
beta_i = -(1-alpha)/alpha H_a partial_i theta_a,
F_uv = -(1-alpha)/alpha[(partial_u H_a)(partial_v theta_a)
                        -(partial_v H_a)(partial_u theta_a)].
```

Writing `m=(1-alpha)/alpha`, the exact exterior derivative is

```text
d beta_R = -m dJ_x wedge dtheta,
dJ_x = J_xp dp + J_xx dtheta + J_xK dK.
```

The `d^2theta` term vanishes, and the `J_xx` contribution cancels because it is
the symmetric Hessian of the scalar circulation `J` contracted
antisymmetrically. The mixed `J_xp` and `J_xK` terms remain. At `(0,0)`, the
`J_xp` contribution is `-222183/2800000`; the `J_xK` contribution is zero at
the center but has exact nonzero gradient `(1989/40000,2457/40000)`. Their
exact jet sum has zero residual against `d beta_R`. Exact rational Taylor
arithmetic also gives

```text
Omega_uv = 7/48,
F_uv = -222183/2800000,
F_uv/Omega_uv = -666549/1225000,
grad(F/Omega) = (54539433/43750000, 11560887/21875000).
```

The nonzero quotient gradient proves the relation is not a constant scalar
identity. Setting `gain=0` or `alpha=1` makes `F=0` while leaving `Omega=7/48`;
doubling gain doubles `F`. The response theorem uses the fixed-tick cycle sum.
The unchanged legacy sample mean is not promoted to that curvature response.

## Benchmark D — same-model zero-set obstruction

Use the continuous D0 diagonal population specialization already proved in the
Benchmark-D Lindblad package:

```text
A = (1/5)(K^T-I)-(1/25)I,
c = (1/125) 1,
O = diag(1,2,3,4,5),
xbar = -A^(-1)c.
```

The exact branch is normalized and uniformly positive (`xbar_j >= 4/69`). No
floor, clipping, projection, or normalization repair is used. Declare the CWT
projective encoding from that actual branch,

```text
psi_j = sqrt(xbar_j),       theta_j=0.
```

It is a smooth positive real normalized lift, so
`A_i=-i<psi|partial_i psi>=-(i/2)partial_i sum_j xbar_j=0` and
`Omega_bd=0` exactly. The same exact `A,c,O` identity yields

```text
F_bd = -28888766872100000000000 / 235345963257301712101 != 0.
```

Therefore no finite scalar relation `F=kappa Omega`, and no frozen
zero-preserving homogeneous linear tensor map applied to this `Omega`, can
reproduce the response for this encoding/readout. The zero-set argument does
not rule out arbitrary nonlinear or affine `Omega`-only maps, and it does not
assert that every possible projective encoding is trivial.

The projective vector is not the mixed density `rho=diag(xbar)`. Separately,
the diagonal density family commutes and has identity Uhlmann link unitaries
and zero holonomy phase. That mixed-state observation is not used to prove the
projective result.

## Artifact and execution policy

The standalone Typer CLI has `status`, `run`, and `verify` commands. Artifact
generation is refused unless every natural gate passes. Test overrides are
monotone fail-only: `True` can never rescue a natural failure. Artifacts are
strict UTF-8/LF and isolated under this experiment. Material sources use a
declared canonical UTF-8/LF hash domain. Canonical gate ownership and case
dispositions are immutable ordered records with independent fingerprints;
semantic validation requires the exact unique gate order and both natural and
final PASS states. Predecessor artifact trees are raw-byte, recursive,
path/type-bound ordinary-file closures; every component from the fixed trust
anchor is checked for symlinks/reparse points and resolved containment.
Artifact generation rejects output overlap with sources, authorities,
predecessors, or protected artifacts before creating a directory or writing a
byte. Predecessor nonmutation is derived from pre/post inventories rather than
self-declared. No predecessor artifact is used as empirical data.
