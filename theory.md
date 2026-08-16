## 1. Scope & Motivation

Causal Web Theory (CWT) posits that observed dynamics emerge from graph-local propagation with density-dependent delays. The baseline transport kernel is local, but the current implementation also uses global estimation, normalization, control, and readout operations; the full stack is therefore not universally strictly local. Three interacting layers capture distinct aspects of evolution:

* **Q-layer**: stochastic amplitude flow (probability mass on nodes/edges),
* **Θ-layer**: phase/coherence field that steers interference-like behavior,
* **C-layer**: classicalization/readout producing macroscopic outcomes.

We “bake in” a geometry on the **space of control parameters** that govern the substrate and layer couplings. The **CWT Geometric Tensor (CGT)** is the standard pullback quantum geometric tensor applied to the declared CWT state map: its **real** part is a sensitivity **metric** and its **imaginary** part is a **Berry-like curvature** that diagnoses oriented/path-dependent geometry. A physical bias or pumping law requires an explicit response coupling, a non-degenerate readout, and the later alignment assumptions; it does not follow from CGT curvature alone. This separates standard projective-state geometry from the still-unproved CWT-specific state-map and response claims.

### 1.1 Empirical status and layer separation

The present theory has two empirically distinct layers.

**Passive CGT diagnostic layer.** Given a substrate, a branch state \(\Psi_*(\lambda,b)\), and a control manifold \(\mathcal M\), the CGT
\[
\mathcal C_{ij}=\langle \partial_i\Psi|\Pi_\perp|\partial_j\Psi\rangle
\]
describes local sensitivity, curvature, and possible transition structure of the branch. In this passive mode, \(g=\mathrm{Re}\,\mathcal C\) and \(\Omega\) are diagnostic fields. They do not, by themselves, imply that every substrate has a \(\mathrm{tr}(g)\) ridge at every independently defined transition. The passive transition-ridge claim is regime-dependent.

**Active geometric-control layer.** Let $R(\gamma)$ be the response to one oriented loop and define
\[
\Delta R_\gamma=R(\gamma)-R(\gamma^{-1}),\qquad
R_{\rm anti}(\gamma)=\frac{\Delta R_\gamma}{2}.
\]
The conditional Stokes construction assumes that an adiabatic/tangent-response reduction supplies a local response one-form $B^{(R)}=B_i^{(R)}d\lambda^i$ such that
\[
R_{\rm anti}(\gamma)=\oint_\gamma B^{(R)}+r_\gamma
=\int_{S_\gamma}\mathcal F^{(R)}+r_\gamma,
\qquad
\mathcal F^{(R)}=dB^{(R)}
=\frac12\mathcal F^{(R)}_{ij}d\lambda^i\wedge d\lambda^j.
\]
Deriving this reduction and a deterministic or stochastic rate for $r_\gamma$ is open; smooth history-dependent response alone does not imply it. For a specified shrinking-loop family with nonzero leading flux, the stronger relation $R_{\rm anti}=\kappa_1\Phi_\gamma+o(\Phi_\gamma)$ requires non-degenerate coupling/readout, $r_\gamma=o(\Phi_\gamma)$, and the integrated-relative alignment condition
\[
\int_{S_\gamma}\left(\mathcal F^{(R)}-\kappa_1\Omega\right)=o(\Phi_\gamma),
\qquad \Phi_\gamma=\int_{S_\gamma}\Omega.
\]
The coefficient $\kappa_1$ may be zero. The present Gate A implementation feeds $\Phi_\gamma$ into the memory/readout construction, so it is a flux-conditioned construction check rather than independent evidence for this stronger law.

External evidence remains non-supportive. OEDI's archived vector is exactly reconstructed post hoc from canonical bytes at pinned official IEEE123 test-system commit `7c8bcca...`, a source consistent with the old numbers; this does not prove the original run's source/parser provenance. The reconstruction refutes the old positive interpretation: its legacy parser creates 84 isolates and omits transformer/regulator connectivity, corrected centrality reverses, ten dependent pairs reuse five profiles, and alpha is a tautological rating/temperature-ignorant dimensionless shape ratio. The packaged profiles' measurement provenance is unspecified. A separately frozen same-package passive diagnostic produced one completed result via one explicitly authorized byte-identical recovery after a documented aborted-no-result attempt, using 61 prespecified confirmation profiles. All 77 admitted calibration/confirmation files passed QC, but the primary association was $T=0.013066368743938832<0.10$ with one-sided conditional bus-bundle QAP $p=0.39696$ (99% Clopper-Pearson Monte Carlo interval for the permutation-tail probability $[0.39296862162223856,0.4009491374352013]$; 99,999 draws, no extension). The conditional random-label null was not rejected, the minimum-effect threshold was unmet, and leave-one/lateral sign stability failed. This supplies no support for that auxiliary passive locality diagnostic, but it is not proof of exact absence and neither validates nor falsifies CGT/CWT. It is not active-loop, ridge, topology, noise, field/physical, independent-replication, population, or generalization evidence. Chicago has endpoint/schema readiness but no tracked quantitative payload result.

The frozen [confirmation result](cwt-sim/experiments/oedi_ieee123_reconstruction/artifacts/prospective_confirmation/REPORT.md), [aborted-no-result incident](cwt-sim/experiments/oedi_ieee123_reconstruction/artifacts/execution_incidents/attempt_001_aborted_no_result.json) (`SHA-256 ba58eb84f715ebf50cb2935dc6ba616c5c0a4a8f169f774a3b9c35d80b6cbd28`), and [authorized recovery record](cwt-sim/experiments/oedi_ieee123_reconstruction/artifacts/execution_incidents/attempt_002_completed_protocol_decision.json) (`SHA-256 080a357e9ff2657f7486e7e08e4ea409bf5d3463606c72bd6e334fd16aff3cc8`) are the durable execution trail. No post-hoc OEDI rescue analysis is authorized by this result.

---

## 2. Substrate, State, and Layers

### 2.1 Graph Substrate

Let $G=(V,E)$ be a directed/weighted graph with $|V|=N$. Each edge $(m\to n)$ has weight $w_{nm}\ge 0$ and local **delay** $\tau_{nm}>0$. Nodes carry a **density** variable $\rho_n\ge 0$. Global or regional aggregates are denoted $\rho,\tau$.

Phase 1 of the laboratory toggles between canonical ensembles to stress-test curvature behaviour: the deterministic
`ring3` reference, random regular graphs with fixed mean degree, small-world and scale-free families, Erdős–Rényi
and Barabási–Albert draws, a toroidal lattice (`periodic_lattice`) that enforces periodic boundaries, and a
Watts–Strogatz sweep with rewiring probability $p\in\{0,0.01,0.10\}$. Comparing their curvature tiles and topology
descriptors (clustering, path length, degree variance, assortativity) reveals how shortcuts, heavy-tailed degree
distributions, or toroidal boundary conditions influence ridge sharpness.

### 2.2 Layer Fields

At discrete simulation step $s$:

* **Q-layer:** nodewise probabilities $p^{(Q)}_n(s)\ge 0$, $\sum_n p^{(Q)}_n=1$.
* **Θ-layer:** phases $\theta^{(\Theta)}_n(s)\in \mathbb{R} \pmod{2\pi}$, optionally edge phases for transport.
* **C-layer:** readout variables $R(s)$ that map to classical outcomes.

### 2.3 Complex State for Geometry

For a fixed branch label $b$ and **control parameters** $\lambda\in\mathcal{M}$, or for a declared operational state map produced by an external runner, define the normalized branch state

$$
\Psi_{*,n}(\lambda,b)=\sqrt{p^{(Q)}_n(\lambda,b)}\,e^{\,i\,\theta^{(\Theta)}_n(\lambda,b)},\qquad \sum_n |\Psi_{*,n}|^2=1.
$$

When branch labels are not explicit, $\Psi(\lambda)$ means this declared branch-resolved or operationally fixed state map. Gauge freedom: $\Psi\to e^{i\phi(\lambda)}\Psi$ leaves observables below invariant.

### 2.4 Control/Parameter Manifold

The **parameter manifold** $\mathcal{M}$ contains slow knobs that shape kernels and couplings. Minimally:

$$
\lambda = (\rho,\tau),\quad \text{optionally}\quad (\rho,\tau,\zeta,\kappa,\ldots)
$$

* $\rho$: mean occupancy or injection density,
* $\tau$: density-dependent delay scale, $\tau\!=\!\tau(\rho)$ allowed,
* $\zeta$: Q–Θ coupling strength (phase-amplitude feedback),
* $\kappa$: proposed transport anisotropy/resistance control. Every positive value of the current uniform scalar cancels inside column normalization, while $\kappa=0$ triggers the degenerate identity/self-loop fallback. Neither implements directional anisotropy; a direction-dependent non-cancelling operator is still required.

---

## 3. Axioms

**A1 (Graph-local transport).** Baseline propagation per time step uses local neighborhoods in $G$, with delays $\tau_{nm}$ and weights $w_{nm}$. Geometry estimation, control, and readout may be global. In the implementation, examples include full-state Pancharatnam gauge fixing, global normalization after `geom_bias`, a global-mean isolated-node delay fallback, and centrality-derived \(\Xi\).

**A2 (Operational state map & normalization).** A predeclared observation-to-$(p,\theta)$ map and branch-selection rule determine $\Psi=\sqrt{p^{(Q)}}e^{i\theta^{(\Theta)}}$ up to gauge, with $\|\Psi\|=1$. Uniqueness is conditional on those declared choices, not model-independent.

**A3 (Passive geometric diagnostics).** For a stable branch \(\Psi_*(\lambda,b)\), the CGT defines a metric and curvature on the control manifold. The metric identifies parameter sensitivity; the curvature identifies oriented loop structure. Passive transition-ridge predictions require an overlap-safe, transition-localized regime and are not assumed universal across all substrates.

**A4 (Active geometric control).** When the model is actively driven around a closed control loop, a declared connection-derived phase-kick can enter the \(\Theta\)-layer. If an adiabatic/tangent-response reduction yields a local response one-form \(B^{(R)}\), its leading orientation-odd half-response is governed by \(\mathcal F^{(R)}=dB^{(R)}\). Deriving that reduction for CWT is open. Proportionality to CGT flux additionally requires response-curvature alignment and non-degenerate coupling/readout; it is not implied by nonzero \(\Phi_\gamma\) alone. Direct curvature-bias source terms are optional exploratory actuation channels unless independently validated.

**A5 (Topological sectors).** First-Chern quantization requires a closed oriented two-dimensional parameter surface and a smooth isolated/gapped projector or invariant subspace. Eigenvector gauges need only be smooth patchwise and may require transition functions; a single global smooth gauge is generally unavailable in a nontrivial bundle. Periodic FHS/QWZ calculations use the special case $T^2$, while QP-1 uses the sphere quotient $S^2$. Outside a closed-surface/gapped-projector setting, curvature flux is geometric rather than topologically quantized.

**A6 (Classicalization and readout discipline).** Readout maps from \((p^{(Q)},\theta^{(\Theta)})\) to outcomes must be declared before fitting. For primary validation, readouts should not contain \(\Phi_\gamma\), \(\Omega\), or loop orientation explicitly; geometric quantities are predictors of response, not definitions of the response.

---

## 4. The CWT Geometric Tensor (CGT)

### 4.1 Definition

Let $\partial_i\equiv \partial/\partial\lambda^i$ and the projector off the state ray be
$\Pi_\perp(\lambda)=I-|\Psi\rangle\!\langle\Psi|.$
Define the **CGT**

$$
\boxed{\; \mathcal{C}_{ij}(\lambda)=\langle \partial_i\Psi|\,\Pi_\perp\,|\partial_j\Psi\rangle\;}
$$

with decomposition

$$
\boxed{\; g_{ij}=\mathrm{Re}\,\mathcal{C}_{ij} \quad \text{(metric)},\qquad \Omega_{ij}=2\,\mathrm{Im}\,\mathcal{C}_{ij} \quad \text{(Berry-like curvature)}\;}
$$

The connection form $\mathcal{A}_i=-i\langle\Psi|\partial_i\Psi\rangle$ satisfies $\Omega_{ij}=\partial_i\mathcal{A}_j-\partial_j\mathcal{A}_i=2\,\mathrm{Im}\,\mathcal C_{ij}$.

### 4.2 Discrete Estimators (Simulation-Ready)

Let $\Psi_0=\Psi(\lambda_0)$, and forward steps $\Psi_i=\Psi(\lambda_0+\delta_i\hat e_i)$, $\Psi_j$, $\Psi_{ij}$. Normalize each.

**Metric:**

$$
\Delta_i\Psi=(\Psi_i-\Psi_0)/\delta_i,\quad \Delta_i^\perp=\Delta_i\Psi-\Psi_0\langle\Psi_0|\Delta_i\Psi\rangle,\quad
\boxed{\; g_{ij}\approx \mathrm{Re}\,\langle\Delta_i^\perp|\Delta_j^\perp\rangle\;}
$$

**Curvature (Wilson loop/FHS):**

$$
W=\langle\Psi_0|\Psi_i\rangle\,\langle\Psi_i|\Psi_{ij}\rangle\,\langle\Psi_{ij}|\Psi_j\rangle\,\langle\Psi_j|\Psi_0\rangle,\quad
\boxed{\; \Omega_{ij}\approx \dfrac{\arg W}{\delta_i\,\delta_j}\;}
$$

Both are gauge-invariant; reduce steps if overlaps become tiny.

**Sign convention.** Repository outputs use the Wilson-loop convention above together with \(\mathcal A_i=-i\langle\Psi|\partial_i\Psi\rangle\) and \(\Omega=+2\,\mathrm{Im}\,\mathcal C\). The QP-1 analytic connection and Wilson estimator then agree, including sign; older opposite-sign statements were an internal convention error.

---

## 5. Dynamics with Geometric Corrections

We write baseline local updates and then add geometric terms.

### 5.1 Baseline Q-Layer (Amplitude Transport)

Let $K_{nm}(\rho,\tau,\kappa)$ be a stochastic kernel induced by edges and delays (e.g., degree-normalized biased walk or an exponential delay weight). One generic form:

$$
K_{nm}=\frac{w_{nm}\,\phi(\tau_{nm};\tau,\rho,\kappa)}{\sum_{k} w_{km}\,\phi(\tau_{km};\tau,\rho,\kappa)},\quad \phi>0.
$$

Update (before geometry):

$$
\tilde p^{(Q)}_n(s+1)= (1-\eta)\,p^{(Q)}_n(s) + \eta\sum_m K_{nm}(\cdot)\,p^{(Q)}_m(s),\quad p^{(Q)}\gets\mathrm{Norm}(\tilde p^{(Q)}).
$$

$\eta\in(0,1] $ is a mixing coefficient; Norm renormalizes.

### 5.2 Baseline Θ-Layer (Phase/Kuramoto-like)

$$
\theta^{(\Theta)}_n(s\!+\!1)=\theta^{(\Theta)}_n(s)+\omega_n(\rho,\tau) + \sum_m J_{nm}(\zeta)\,\sin\big(\theta_m-\theta_n\big).
$$

$\omega_n$ encodes delay-to-phase clocking; $J_{nm}$ encodes coherence coupling strength.

### 5.3 Active geometric coupling channels

In active-control experiments, the scheduler may apply geometric terms during a closed loop \(\gamma\subset\mathcal M\). Two channels are distinguished.

#### 5.3a Connection / phase-kick channel

The implemented active channel is the connection-driven \(\Theta\)-layer kick
\[
\theta_n \leftarrow \theta_n + a_{i,n}(\lambda)\Delta\lambda^i,
\]
where \(a_{i,n}\) is a gauge-fixed local connection or local phase-response field. Only relative phases and edge phase differences are physically relevant. A global Berry phase by itself is not an observable nodewise force.

For small adiabatic loops, the conditional construction in Section 1 is $R_{\rm anti}=\int_{S_\gamma}\mathcal F^{(R)}+r_\gamma$ after an adiabatic/tangent reduction supplies the local response one-form. Deriving that reduction and the rate/sense of $r_\gamma$ for the concrete update remains open. The CGT-flux law further requires the integrated-relative alignment and nondegeneracy conditions stated there. The full CCW/CW difference is $\Delta R_\gamma=2R_{\rm anti}$. In repository benchmark C, setting `current_phase_gain=0` leaves a nonzero signed Wilson flux but makes the excess-circulation CCW/CW response exactly zero, so $\kappa_1=0$ is an explicit counterexample to any unconditional implication from flux to response.

Current internal Gate A output is not independent validation of this phase-kick mechanism because `memory_current_coupled` receives the signed flux and its result enters the readout. It can test sign and scaling consistency of the constructed channel. Independent validation requires a predeclared response that does not contain \(\Phi\), \(\Omega\), or orientation.

#### 5.3b Direct curvature-bias channel

A direct curvature-bias term may be included as an exploratory actuator, for example as a conservative edge-current correction rather than a node source term. The direct \(\Omega\)-bias pathway is not validated as an independent leading mechanism. Claims about it remain exploratory until an auditable experiment with an independent readout and preregistered ablations finds a regime where \(\Omega\)-specific perturbations measurably change the response.

### 5.4 Conservation & Stability

* Ensure $\sum_n p^{(Q)}_n=1$ each step.
* Clip geometric additions if needed to keep $\tilde p^{(Q)}_n\ge 0$ before normalization.
* Use phase unwrapping and small $|\Delta\lambda|$ to maintain numerical stability of $\mathcal{A},\Omega$.

### 5.5 Operator Form (Optional)

Define an effective one-step map $U(\lambda)$ (or generator $H_\mathrm{eff}$) acting on $\Psi$. Band-resolving $U$ in a graph-spectral basis allows bandwise CGT, topological indices, and mode-selective analysis.

---

## 6. Control on the Parameter Manifold

### 6.1 Action for Schedules

As a design postulate, when the experimenter or scheduler controls $\lambda(s)$, one may assign an action

$$
S[\lambda]=\int ds\,\Big(\tfrac{1}{2}g_{ij}(\lambda)\,\dot\lambda^i\dot\lambda^j + \mathcal{A}_i(\lambda)\,\dot\lambda^i - U(\lambda;G)\Big).
$$

* The **metric term** penalizes fast moves where the system is sensitive.
* The **connection term** supplies an oriented/gyroscopic contribution; its antisymmetric curvature force does no ordinary instantaneous work.
* $U$ encodes objectives/constraints (e.g., holding density ranges, energy budgets).

Euler–Lagrange yields geodesic-plus-Lorentz equations on $\mathcal{M}$:

$$
\frac{d}{ds}\Big(g_{ij}\dot\lambda^j+\mathcal{A}_i\Big)-\tfrac{1}{2}\partial_i g_{jk}\,\dot\lambda^j\dot\lambda^k - (\partial_i\mathcal{A}_j)\,\dot\lambda^j + \partial_i U=0.
$$

This dimensionless/design-only action can motivate **auto-schedulers** that choose smooth loops to probe curvature while avoiding high-$g$ ridges. The repository does not derive it from the discrete dynamics, and a continuum claim requires an explicit step-size limit plus consistent physical units/scaling (or an explicit nondimensionalization) for every term.

---

## 7. Observables & Phases

### 7.1 Geometry Observables

* **Metric scalars:** $\mathrm{tr}\,g$, $\sqrt{\det g}$. Large values flag critical sensitivity.
* **Curvature density:** $|\Omega_{ij}|$ and its sign.
* **Loop flux:** $\Phi_\gamma=\oint_\gamma \mathcal{A}_i\,d\lambda^i=\tfrac{1}{2}\iint_\Sigma\Omega_{ij}\,d\lambda^i\wedge d\lambda^j$.
* **Topological index (on a closed oriented surface $\Sigma$):** $C=\frac{1}{2\pi}\int_{\Sigma}\Omega\in\mathbb{Z}$ for a smooth gapped projector with patchwise gauges. The FHS/QWZ implementation specializes to $\Sigma=T^2$.

### 7.2 Readout/Response Observables

Define the response to one oriented closed loop $\gamma$ from C-layer outcome probabilities:

$$
R(\gamma)=\sum_X w_X P_X^{\,\gamma},\qquad
R_{\rm anti}(\gamma)=\frac{R(\gamma)-R(\gamma^{-1})}{2},\qquad
\Delta R_\gamma=2R_{\rm anti}(\gamma),
$$

with weights $w_X$ to target specific outcomes. If an adiabatic/tangent reduction yields the response one-form, the conditional Stokes identity and unspecified remainder are those in Section 1. The linear CGT-flux law additionally requires integrated-relative alignment, a non-degenerate coupling/readout, and a controlled remainder; its coefficient may vanish. The repository's OEDI/Chicago summaries do not test this loop-response law.

### 7.3 Phase Structure

* **Critical frontiers:** in overlap-safe regimes where branch response is transition-localized, ridges in $\mathrm{tr}\,g$ can co-locate with independently defined transition gradients; this is substrate/regime-dependent.
* **Topological plateaus:** the full closed-surface Chern integral is stable under smooth projector deformations that keep the isolating gap open. Ordinary loop flux is not generally invariant under path noise.
* **Order ↔ disorder regions:** inferred from long-time variance of $p^{(Q)}$ and phase locking of $\theta^{(\Theta)}$.

---

## 8. Validation Gates (Theory-Level Tests)

**Gate A — Flux-conditioned construction check.** Drive a rectangular loop in $(\rho,\tau)$ and verify that the implemented flux-conditioned memory/readout has the intended sign and scaling. Because the current readout path receives $\Phi_\gamma$, this gate does not independently validate $R_{\rm anti}\propto\Phi_\gamma$. An independent Gate A must use a preregistered readout that contains no $\Phi$, $\Omega$, or orientation input.

**Gate B — Critical Ridge Finder.** Grid-scan $(\rho,\tau)$; compute $\mathrm{tr}\,g$ and $|\Omega|$. Test co-location against an independently and ex ante defined transition marker on held-out data. Current transition labels use post-hoc 25th/75th-percentile thresholds on the analyzed grid, so a "positive co-location regime" is not yet ex ante identifiable. No tracked OEDI or Chicago artifact closes this gate.

**Gate C — Protocol/noise robustness.** Add noise to ordinary $\lambda$-loops and measure estimator/readout stability without calling it topological protection. A separate topology-robustness gate must integrate the Chern number over the complete closed parameter surface and verify that the spectral projector remains smooth and gapped under perturbation; ordinary loop response is not topologically protected.

The current `gateC_topology_robust` runner is therefore historical in name only: it is an internal-synthetic, flux-conditioned loop/noise construction. Its `pure_state_criteria_met` output records only coherence/overlap threshold passage; it does not establish quantization, and the runner implements no mixed-state fallback.

**Gate D — Bell/CHSH Modulation (optional).** If a CHSH gate exists, correlate deviations in correlators with $|\Omega|$ along small loops.

---

## 9. Limiting Cases & Consistency

* **Parameter-independent state:** if $\partial_i\Psi=0$, then $g=0$ and $\Omega=0$. Merely holding a knob static along one trajectory does not imply that derivative vanishes.
* **Phase-randomized ensembles:** random phases do not generally force a single-realization curvature to zero. Suppression requires a specified ensemble/dephasing limit and must be demonstrated for the chosen estimator.
* **Uniform amplitudes:** flat $p$ can still have parameter-dependent relative phases and therefore nonzero metric or curvature. Geometry vanishes only when the projective state is parameter independent.
* **Gauge invariance:** all observables built from inner products and loops are invariant under $\Psi\to e^{i\phi(\lambda)}\Psi$.

---

## 10. Implementation Notes (drop-in to repo)

### 10.1 File/Section Placement

* **theory/Theory.md:** add Sections 4–8 as above (CGT, Dynamics with Geometry, Control, Observables, Gates).
* **metrics/refine.py:**

  * `metric_tensor_tile(lambda0, deltas) -> g_ij`
  * `berry_curvature_tile(lambda0, deltas) -> Omega_ij`
  * `geom_score = α*tr(g) + β*sqrt(det g) + γ*abs(Omega_ij)`
* **metrics/triage.py:** include geometry-aware triage using `geom_score`.
* **orchestrator/**: add `ParameterPath` (line, rectangle, Lissajous) and `with_geom=True` to inject phase kicks and Q-bias.

### 10.2 Pseudocode — CGT Estimators

```
# Build Psi from current fields at lambda:
Psi = normalize(sqrt(pQ) * exp(1j * theta))
# Metric (per two knobs i,j):
Delta_i = (Psi_i - Psi_0) / delta_i
Delta_i_perp = Delta_i - Psi_0 * (Psi_0.conj() @ Delta_i)
Delta_j = (Psi_j - Psi_0) / delta_j
Delta_j_perp = Delta_j - Psi_0 * (Psi_0.conj() @ Delta_j)
g_ij = real(Delta_i_perp.conj() @ Delta_j_perp)
# Curvature (FHS Wilson plaquette):
W = (Psi_0.conj() @ Psi_i) * (Psi_i.conj() @ Psi_ij) * \
    (Psi_ij.conj() @ Psi_j) * (Psi_j.conj() @ Psi_0)
Omega_ij = angle(W) / (delta_i * delta_j)
```

### 10.3 ParameterPath API (sketch)

```
class ParameterPath:
    def __init__(self, kind, center, extents, steps): ...
    def step(self, s):
        # returns lambda_s, Delta_lambda
        ...
```

Integrate into the orchestrator; on each step, compute $\mathcal{A}_i\Delta\lambda^i$ for phases and $\Gamma_n$ for Q bias.

### 10.4 Numerical Tips

* Use small finite steps and symmetric differences where possible.
* Time-average $p,\theta$ over short windows before building $\Psi$ to reduce noise.
* Regularize overlaps: if $|\langle\Psi_a|\Psi_b\rangle|<\epsilon$, reduce step or smooth fields.

---

## 11. Relationships to Established Constructs

* **Quantum Geometric Tensor (QGT):** CGT mirrors QGT mathematically, with metric (sensitivity) and curvature (holonomy). The key difference is that CWT’s $\Psi$ is built from **graph-local** amplitude/phase fields rather than an eigenstate of a Hamiltonian.
* **Causal Set/Discrete Spacetime:** CWT’s density-dependent delays mimic emergent metric effects; CGT lives on control space, not spacetime, yet it influences macroscopic outcomes via path dependence.
* **Adiabatic Pumps/Thouless Pump:** CGT geometry suggests an analogy to adiabatic pumping, but a directional C-layer bias follows only after deriving a response coupling and the response-curvature/CGT-curvature alignment conditions.

---

## 12. Glossary

* **CGT:** CWT Geometric Tensor $\mathcal{C}_{ij}$ from $\Psi(\lambda)$.
* **Metric $g_{ij}$:** real part of CGT; sensitivity to parameter changes.
* **Curvature $\Omega_{ij}$:** imaginary part (×2); geometric “magnetic field.”
* **Connection $\mathcal{A}_i$:** Berry-like vector potential on $\mathcal{M}$.
* **Loop Flux $\Phi_\gamma$:** geometric phase over closed parameter loops.
* **Triage Score:** scalar combining $\mathrm{tr}\,g$, $\sqrt{\det g}$, and $|\Omega|$ to select interesting regimes.

---

## 13. Minimal Working Example (conceptual)

1. Choose $\mathcal{M}=(\rho,\tau)$. Define a rectangular loop (center, widths, steps).
2. Run the system; at each step, build $\Psi$. Any nodewise $a_{i,n}\Delta\lambda^i$ phase field or direct $\Gamma$ amplitude bias is an exploratory actuator requiring its own gauge-covariant definition; a scalar Berry connection supplies only a common phase.
3. After the loop, compute $\Phi_\gamma$ via Wilson loop and measure $R(\gamma)$ from C-layer outcomes, then form $R_{\rm anti}$ from the reversed pair.
4. Reverse loop orientation; verify the estimator sign flip in $\Phi_\gamma$. With an independent readout, test rather than assume whether $R_{\rm anti}$ is nonzero and aligned with $\Phi_\gamma$; allow the null $\kappa_1=0$ outcome.

---

## 14. Predictions and regime conditions

The theory makes two distinct classes of prediction.

### 14.1 Active loop-response prediction

For an actively driven, overlap-safe, adiabatic closed loop \(\gamma\), use the response definitions from Section 7: \(\Delta R_\gamma=R(\gamma)-R(\gamma^{-1})\) and \(R_{\rm anti}=\Delta R_\gamma/2\). The conditional Stokes identity in Section 1 applies only after an adiabatic/tangent-response derivation supplies \(B^{(R)}\), with its unproved reduction error collected in \(r_\gamma\). Reversing orientation changes the sign of the line/surface contribution, not necessarily every history-dependent remainder.

For a specified shrinking-loop family with nonzero leading flux, \(R_{\rm anti}=\kappa_1\Phi_\gamma+o(\Phi_\gamma)\) requires the integrated-relative alignment condition, \(r_\gamma=o(\Phi_\gamma)\), a non-degenerate coupling, and an independently measured response. Equivalently, \(\Delta R_\gamma=2\kappa_1\Phi_\gamma+o(\Phi_\gamma)\). Metric-only scalar surrogates have no orientation sign, but rejecting one linear-correlation surrogate does not reject every orientation-null model.

This is a conditional Stokes construction, not a generic smooth-response theorem. Current Gate A is circular as an evidentiary test because flux enters the memory/readout, and the repository contains no auditable OEDI or Chicago loop-response artifact.

### 14.2 Passive transition-ridge prediction

The available conditional perturbation statement is narrower: for an isolated simple spectral branch, a shrinking gap can amplify the metric when the relevant derivative matrix elements are nonzero and the eigenprojector/non-normal conditioning remains controlled. It does not imply co-location with a separately defined transition gradient.

Co-location between \(\mathrm{tr}(g)\) and a transition marker such as \(\|\nabla r\|\) is an open empirical hypothesis. Any claimed regime must be defined ex ante using covariates available before observing co-location, and the transition labels must also be fixed independently. The sign and magnitude of
\[
\mathrm{Spearman}(\mathrm{tr}(g),\|\nabla r\|)
\]
depend jointly on delay-distribution shape and coupling regime. Constant or degenerate delays can collapse the passive signal. Changing delay-distribution shape can weaken or flip the signal. Cross-substrate comparison must therefore report topology, delay distribution, coupling parameters, valid-tile fraction, Fubini-Study safety, and the range of the independent transition marker.

Internal synthetic Gate B runs are exploratory. Their transition labels are assigned post hoc from the same grid, and their cellwise bootstrap does not establish out-of-seed or spatially blocked generalization. OEDI's reconstructed five-profile slice is post hoc, dependent, and based on a flawed historical graph; it is not a ridge test. Its separate 61-profile same-package distance/dissimilarity diagnostic was prespecified and executed, but failed its primary $T$ and QAP gates and its leave-one/lateral sign-stability rules. That negative auxiliary-locality result is not a CGT ridge test or proof of absence. Chicago supports only endpoint/schema readiness. Passive external ridge co-location therefore remains untested.

### 14.3 Negative controls

Not every readout is expected to be holonomy-driven. Readouts may be dominated by path length, perimeter drift, or non-geometric relaxation. Evidence for the conditional alignment law requires an independent readout, orientation reversal, controlled adiabatic/remainder diagnostics, a preregistered shrinking-area family, and allowance for the null \(\kappa_1=0\) outcome.

---

## 15. Closing Remarks

The CGT reframes how **control** may shape **emergence** via geometry on parameter space. Baseline graph transport is local and mass preserving in the ideal unbiased branch, making normalization redundant there. The implemented geometry pipeline nevertheless includes potentially global estimation, control, normalization, fallbacks, and readouts. The defensible scope is local graph transport with potentially global estimation/control/readout, not universally strict locality of the full dynamics.

---

## 16. Analytic Operator Form (Expanded)

We formalize three complementary operator views that enable spectral analysis, eigenstate geometry, and perturbation theory.

### 16.1 Non-Hermitian Linear Map (Projective Dynamics)

Define a step operator L(lambda) in C^{N x N} acting on Psi such that

|Psi'⟩ = L(lambda) |Psi⟩ / || L(lambda) |Psi⟩ ||.

• Interpretation: transport + delay + coherence packed into a single linear (generally non-unitary) map, followed by projective normalization.

• Biorthogonal spectrum: right/left eigenpairs L |u_a^R⟩ = mu_a |u_a^R⟩, ⟨u_a^L| L = mu_a ⟨u_a^L|, with ⟨u_a^L|u_b^R⟩ = delta_ab.

• Critical-ridge hypothesis: crossings or exceptional points can produce large geometric response only when the relevant derivative matrix elements are nonzero and the eigenprojector/branch remains regular enough for the estimator. A small gap alone does not guarantee a spike.

• Eigenstate geometry: after computing dual left/right vectors with ⟨u_a^L|u_a^R⟩=1, define A_i^(a) = -i ⟨u_a^L| ∂_i u_a^R⟩ and Omega_ij^(a) = ∂_i A_j^(a) − ∂_j A_i^(a). Equivalently, with Q_ij^LR = ⟨∂_i u_a^L|(I-|u_a^R⟩⟨u_a^L|)|∂_j u_a^R⟩, the general biorthogonal curvature is F_ij=-i(Q_ij^LR-Q_ji^LR), which may be complex. Only in the normal/Hermitian case u_L=u_R does this reduce to the real pure-state identity 2 Im Q_ij. The current operator-patch code/tests implement only that normal/Hermitian path; general dual-left handling remains open. On a closed oriented parameter surface with a smooth isolated spectral projector and patchwise gauges, the applicable Chern construction requires the corresponding bundle/curvature conditions.

### 16.2 CPTP Superoperator (Density-Matrix View)

Lift to rho = |Psi⟩⟨Psi| and define a completely positive trace-preserving map

E_lambda(rho) = sum_alpha K_alpha(lambda) rho K_alpha(lambda)^†,  with  sum_alpha K_alpha^† K_alpha = I.

• Encodes diffusion, dephasing, and phase kicks via Kraus operators.

• Geometry generalizes to Bures metric and Uhlmann curvature for mixed states; useful under noise.

### 16.3 Transfer/Koopman Operator (Classical–Quantum Split)

Model amplitude transport by a Markov matrix P(lambda) and phases by a diagonal/nearest-neighbor phase operator D_Theta(lambda). The block operator on augmented state captures spectrum via Perron–Frobenius (for P) and phase locking (for D_Theta).

---

## 17. Perturbation Theory Around lambda_0

For the non-Hermitian map in 16.1:

• Eigenvalue shifts: ∂_i mu_a = ⟨u_a^L| (∂_i L) |u_a^R⟩.

• Eigenvector shifts: |∂_i u_a^R⟩ = sum_{b≠a} |u_b^R⟩ [ ⟨u_b^L| (∂_i L) |u_a^R⟩ / (mu_a − mu_b) ].

• Metric/curvature (approx.): construct Q_ij^LR from both derivative left and derivative right vectors and use F_ij=-i(Q_ij^LR-Q_ji^LR). For normal/Hermitian states this reduces to the projected pure-state metric and Omega_ij=2 Im Q_ij used by the current executable tests. Small gaps can amplify the geometry only when the corresponding numerator matrix elements remain nonzero; branch regularity and non-normal conditioning also matter. A general non-Hermitian implementation still needs dual-left eigensolvers, normalization, and complex-curvature tests.

---

## 18. Nodewise Susceptibility Xi_n: Definitions & Options

The exploratory flux/curvature-conditioned actuator Gamma_n = beta sum_{i<j} Omega_ij epsilon^{ij} Xi_n needs a principled Xi_n. It is a designed control input, not a consequence of CGT and not an independent validation channel. We propose three families:

### 18.1 Static Graph Feature (fast, explainable)

Xi_n(static) = [deg(n)]^{b1} [eig_cent(n)]^{b2} / sum_k [deg(k)]^{b1} [eig_cent(k)]^{b2}.

### 18.2 Dynamic State-Dependent (feedback enabled)

Let g_n^(theta) = | sum_m w_nm sin(theta_m − theta_n) |,
g_n^(p)     = sum_m w_nm [sqrt(p_m) − sqrt(p_n)]_+, and
s_n         = | (1/d_n) sum_{m in N(n)} exp(i theta_m) | in [0,1] (local coherence).
Define
Xi_n(dyn) = Norm( g1 |Psi_n|^2 + g2 g_n^(theta) + g3 g_n^(p) + g4 s_n ).
This closes a feedback loop: the state modulates its own geometric sensitivity.

### 18.3 Learned (data-driven)

Xi_n(learn) = sigmoid( a0 + sum_k a_k z_{n,k} ), with features z in { |Psi_n|^2, g_n^(theta), g_n^(p), s_n, degree, centralities }. Train a_k to maximize repeatable pumped bias or task reward.

Recommendation: start with 18.1 for baselines, then 18.2 to study feedback effects.

---

## 19. C-Layer Physics: Concrete Readout Families

We specify three exploratory readout families. The versions below all include loop flux Phi_gamma by construction, so they are flux-conditioned actuators/readouts and cannot validate A6 or an independent `R_anti`–`Phi_gamma` relation.

### 19.1 Stochastic Sampling (Born-like with temperature)

Pick outcome/node X with
P(X=n) = softmax_T( log p_n^(Q) + eta M_n(Phi_gamma) ).
Limits: T → 0 gives argmax; T → ∞ gives uniform.

### 19.2 Threshold/Percolation Readout (network event)

Active set A = { n | p_n^(Q) > p_crit }. Fire if the largest connected component in A exceeds theta_perc * |V|. Memory enters by shifting p_crit -> p_crit − delta(Phi_gamma).

### 19.3 Spiking/Poisson Ensemble

Each node emits spikes with rate r_n = r0 [ c1 p_n^(Q) + c2 s_n + c3 M_n(Phi_gamma) ]_+.
An event occurs if total spikes in a window exceed R_th. Suitable for detector-array analogs.

---

## 20. Research Roadmap (Analytic + Experimental)

1. Build L(lambda) for a minimal graph and test whether gap closings or exceptional points co-locate with ridges in tr(g), including numerator/conditioning controls and null outcomes.
2. Compute biorthogonal Omega^(a) along (rho, tau) loops; with a flux-independent readout, test the conditional alignment law `R_anti ∝ sum_a w_a Phi_gamma^(a)` and allow `kappa_1=0`.
3. First-order perturbation: implement ∂_i L and predict g_ij without stencils; compare to CGT estimates.
4. Xi_n study: A/B 18.1 vs 18.2; quantify stability and effect sizes on pumped bias.
5. C-layer ablations: compare 19.1/19.2/19.3 on the same loops; report which yields the cleanest geometric scaling.

— End of v4.0-CGT-draft extensions —

### 20.1 Stage 0 — Estimator validation on analytic cases

Before large networks, validate CGT estimators where closed forms exist:

* Two-node dimer: one edge with tunable delay/weight. Closed-form Psi, exact FS distance; curvature is zero except at singular reparametrizations.
* Three-node line and ring: small loops in (rho, tau). Hand-derive g_ij from overlaps; curvature should vanish on lines and appear on rings under phase bias.
* Biased random walk with uniform phase: expect Omega = 0 while tr(g) tracks sensitivity of the transport spectrum P(lambda).
  Report estimator error versus step size, and set default deltas from a target relative error.

---

## 21. Numerical Stability and Gauge-Fixing for CGT Estimators

Problem: the Wilson-plaquette curvature
W = ⟨Psi0|Psi_i⟩⟨Psi_i|Psi_ij⟩⟨Psi_ij|Psi_j⟩⟨Psi_j|Psi0⟩
gets unstable when overlaps are small, which happens where curvature is large.

Remedies (use together):

1. Parallel-transport gauge (PTG): rephase each neighbor by Psi_i <- exp(-i * arg ⟨Psi0|Psi_i⟩) * Psi_i, etc., to maximize real-positive overlaps before forming W.
2. Adaptive meshing: halve delta_i, delta_j locally until |⟨Psi_a|Psi_b⟩| >= s_min (e.g., 0.6). Use finer tiles only where needed.
3. Multi-plaquette integration: integrate Omega over many micro-plaquettes and sum their arg W; reduces variance and avoids single-plaquette breakdown.
4. Log-plaquette accumulation: compute log W with numerically stable atan2 on each factor and sum arguments to avoid cancellation.
5. Time/ensemble smoothing: average Psi over a short window before geometry; report error bars via bootstrap or jackknife across windows and micro-plaquettes.
6. Mixed-state fallback: when noise or dephasing is high, switch to the CPTP/Uhlmann construction (Section 16.2) to keep geometry well-defined.
7. Instability detector: flag tiles with min-overlap < s_min and queue them for refined sampling; do not trust single-shot Omega there.

---

## 22. Flux-conditioned memory actuators M_n(Phi_gamma)

These recipes make a designed flux-conditioned memory explicit. Because each inserts `Phi_gamma`, they may test implementation consistency or actuation response, but they cannot serve as independent evidence that CGT flux predicts a readout.

A) Uniform geometric charge: M_n = chi_n * Phi_gamma, with chi_n a fixed weight (e.g., amplitude share |Psi_n|^2 averaged over the loop or normalized centrality). Predicts global, orientation-sensitive bias.

B) Direction-locked memory: M_n = Phi_gamma * s_n * (t_loop dot grad_theta_n), where s_n in [0,1] is local coherence and t_loop the loop’s orientation in parameter space mapped to a preferred transport direction on the graph. Links memory to phase gradients that steer flow.

C) Current-coupled memory: define edge current J_nm = w_nm * sqrt(p_n p_m) * sin(theta_m - theta_n). Let M_n_raw = sum_m J_nm - J_mn (net outgoing). Then use M_n = Phi_gamma * Norm(M_n_raw). Ties memory to a directly computed graph observable.

Report which form is used in each experiment and label it flux conditioned. A is the simplest construction; C incorporates a computed graph current but remains circular for validating the flux law.

---

## 23. Self-consistent dynamics with dynamic Xi_n

Dynamic susceptibility closes a feedback loop. To avoid arbitrariness and instability:

Contractive regime: choose beta and the gamma_k (Section 18.2) so that the composite map (Psi, lambda -> updated Xi) is Lipschitz with constant < 1 in the chosen norm. Start with small beta and ramp.

Outer–inner iteration:

1. Freeze Xi (from previous run or static init), run one loop in M and record geometry and pumped bias.
2. Update Xi from the new Psi fields (Section 18.2), then low-pass filter: Xi <- (1 - kappa) * Xi + kappa * Xi_new.
3. Repeat until ||Delta Xi|| < epsilon and pumped bias stabilizes (orientation flip still flips sign).

Monitors: track spectral gap of L(lambda), min-overlap, tr(g), and a Lyapunov proxy for Theta (Section 25). Abort or ramp when any exceed thresholds.

---

## 24. A low-cost geometric thermometer

Goal: an early-warning scalar that rises near sensitivity ridges without full CGT.

Directional FS estimate: for each knob i, compute d_FS(lambda, lambda + delta_i) = arccos |⟨Psi(lambda)|Psi(lambda + delta_i)⟩|. Define
Theta_geo = sum_i w_i * d_FS^2 / delta_i^2  ≈  sum_i w_i * g_ii.
This uses only two-point overlaps (no Wilson loops). Trigger high-precision curvature when Theta_geo crosses a threshold.

Streaming variant: maintain an EMA of (1 - |⟨Psi_s|Psi_{s+1}⟩|) / step^2 along the schedule; spikes flag sensitive regions online.

---

## 25. Nonlinear effects beyond perturbation

Perturbation around lambda_0 is local. To capture CWT’s nonlinear regimes:

* Continuation and bifurcation: track fixed points or limit cycles of (Q, Theta) as lambda varies; detect saddle-node, Hopf, and period-doubling via Floquet multipliers of the projective map.
* Finite-time Lyapunov exponents (FTLE) for Theta: compute FTLE over neighborhoods to locate chaotic tongues; compare with tr(g) to see where geometry forecasts instability.
* Coarse-grained curvature: when Psi is aperiodic, define Omega from time-averaged plaquettes over an ergodic window; test robustness of pumped bias to phase noise.

---

## 26. Parameter discipline and ablations

To avoid p-hacking and manage Xi choices and C-readouts:

* Pre-registration: for each study, predeclare which Xi family (18.1, 18.2, or 18.3) and which C-layer readout (19.x) will be used.
* Ablation matrix: run all 3 by 3 combinations on identical paths; report effect sizes with confidence intervals. Share configs and seeds.
* Mesh protocol: publish s_min, delta schedules, and refinement rules from Section 21.

---

## 27. Foundational Regimes and Limits (theory clarification)

To make scope and guarantees explicit, we distinguish regimes.

27.1 Discrete-time vs continuous-time

* The primary formulation is discrete steps on a graph with delays. A continuous-time limit is presently a postulate, not a proved consequence of the implementation. Establishing it requires an explicit step-size family, convergence bounds, and consistent units/scaling for delay, coupling, normalization, and control terms.

27.2 Adiabatic small-loop regime

* If an adiabatic/tangent-response reduction gives a leading local line functional under small, slow parameter loops, its orientation-odd half-difference is a surface integral of response curvature. Deriving that reduction for CWT is open. The further law `R_anti = kappa_1 * Phi_gamma + o(Phi_gamma)` requires local alignment between response curvature and CGT curvature plus non-degenerate coupling/readout. No repository result establishes it for an independent external readout, and `kappa_1` may be zero.

27.3 Non-adiabatic regime

* Breakdown indicators: large Fubini–Study distance per step, small eigenvalue gaps of L, or rapid parameter changes. In this regime one should rely on coarse-grained curvature (time-averaged plaquettes) and nonlinear diagnostics (Section 25).

27.4 Mixed-state regime

* Under dephasing/noise, geometry should be read via CPTP/Uhlmann constructions (Section 16.2). Claims about integer-like plateaus are not made in this regime; robustness is still meaningful but quantization is not guaranteed.

---

## 28. Quantization Conditions for Topological Plateaus

We clarify when first-Chern quantization is expected and when it is not.

* Parameter manifold: any closed oriented two-dimensional surface. QP-1 realizes the sphere quotient $S^2$; the FHS/QWZ benchmark realizes periodic $T^2$.
* Spectral gap: a nonzero gap separating a band or invariant subspace of the step operator L from the rest of the spectrum along the loop family.
* Smooth projector/subspace: the isolated spectral projector is smooth on the closed surface. Eigenvector gauges may be defined patchwise with transition functions; a single global smooth eigenvector gauge is not required and is generally incompatible with a nonzero Chern number.
* Consequence: integrated biorthogonal curvature over the closed surface yields the first Chern number C as long as the projector remains smooth and isolated. If the gap closes (exceptional points, band touching), C can jump. With perturbations that preserve the gap/projector conditions, C is stable; outside them, only non-quantized geometric flux should be asserted.

---

## 29. Correspondence Principles (reductions to known models)

These reductions anchor CWT in established dynamics under specific limits.

29.1 Kuramoto reduction (Theta-only)

* If amplitudes are uniform/slow and the Q-layer does not reshape transport on the timescale of Theta coupling, the phase update reduces to a Kuramoto-type model with coupling matrix J. Standard order-parameter analyses apply (synchronization transition, etc.).

29.2 Markov diffusion (Q-only)

* If an explicitly defined dephasing/ensemble limit suppresses the geometric terms, the evolution reduces to a Markov chain with transition matrix K(lambda). Random phases in a single realization do not by themselves guarantee zero metric or curvature.

29.3 Adiabatic pumping (Thouless analog)

* For small, slow loops on a toroidal parameter domain with a gapped invariant subspace, a response may parallel adiabatic pumping only when response curvature aligns with CGT curvature and the coupling/readout is non-degenerate. Topological flux alone does not guarantee a nonzero classical readout.

29.4 Near-unitary map (Schroedinger-like)

* If transport is nearly lossless and the normalization step is replaced by a constant-norm evolution, the composite step approaches a unitary-like map. In that limit, CGT coincides with the standard quantum geometric tensor for the effective band states.

---

## 30. Reparameterization and Gauge Invariance

* State gauge: replacing Psi by e^{i phi(lambda)} Psi leaves the CGT and closed-loop curvature flux invariant; numerics use parallel-transport gauge for stability. A nodewise actuator or pumped readout is gauge invariant only if its control/readout construction is explicitly gauge covariant, which remains an open requirement for the proposed CWT coupling.
* Coordinate change on M: the metric g transforms as a rank-2 tensor under reparameterizations of lambda; curvature is a 2-form. Loop integrals (Phi_gamma) are diffeomorphism-invariant.

---

## 31. Conventions and Defaults (theory-facing)

To minimize arbitrariness in baseline claims and make studies comparable:

* Susceptibility Xi_n: default to static graph feature (degree * eigenvector centrality, normalized).
* Memory term M_n: default to current-coupled form tied to net phase current at each node.
* C-layer readout: default to stochastic sampling (Born-like) with moderate temperature. Alternatives are allowed but must be declared and ablated (Section 26).
* Reporting: always publish loop shape, speed, overlap thresholds, and whether runs are pure-state or mixed-state.

---

## 32. Measurement Cost (conceptual scaling)

* Building Psi at a point in M is O(N) in the number of nodes (assuming sparse ops). Two-point FS distances are O(N). A single Wilson plaquette uses four overlaps; adaptive meshing multiplies by a small refinement factor only near sensitive regions detected by the thermometer. Thus, total cost ≈ tiles * overlaps per tile, with refinement concentrated where it matters. This motivates using the thermometer as a first pass.

---

## 33. Law-waves: slow dynamics of control

* “Law-waves” are a proposed design interpretation for slow, possibly autonomous control-parameter dynamics over M. One may model them with the postulated action in Section 6.1 plus feedback, but that action is not derived from the discrete CWT update. CGT can be used as a proposed control cost/gyroscopic geometry within this design study; it does not by itself generate directional readout bias.

---

### 32.1 Cost envelope and anytime estimators (clarification)

We refine the cost discussion to reflect adaptive meshing realities.

* Let T0 be the number of coarse tiles on the parameter grid. A single Wilson plaquette uses 4 overlaps; let Cplaq denote that unit cost.
* Suppose a fraction f of tiles are flagged for refinement up to depth r_max (each refinement halves both step sizes, creating 4 sub-plaquettes per level). A conservative worst-case multiplier for refined tiles is 4^{r_max}.
* The total work relative to a uniform single-plaquette sweep is then bounded by:
  Work / (T0 * Cplaq) ≤ (1 − f) + f * 4^{r_max}.
* In practice, f is driven by the thermometer and EP proximity; report f and r_max per study.

**Anytime curvature estimator.** On each flagged tile, sample K micro-plaquettes sequentially and stop when the empirical standard error of the mean curvature falls below a preset tolerance or when K hits a hard cap. Publish per-tile CIs and the fraction of tiles that hit the cap.

**Pre-registered stop rules.** Stop refinement when (i) min-overlap ≥ s_min and (ii) CI width ≤ ε on all micro-plaquettes in the tile; else escalate depth by 1 (up to r_max). This makes compute predictable and auditable.

---

### 33.1 Terminology note (law-waves)

“Law-waves” is optional shorthand for a proposed **control-field design model** using the Section 6.1 action. To avoid unnecessary jargon or implying a derived dynamics, papers may omit the term and describe the postulated control model directly.

## 34. Responses to Critical Review: Theory Integrations

34.1 Normalization and CGT (projective map)

* We use the projective map L_hat(psi) = L(lambda) * psi / || L(lambda) * psi ||. The CGT uses projected derivatives (I − |Psi⟩⟨Psi|) * d_i |Psi>, removing any component parallel to |Psi|. Therefore, any scalar rescaling of L (including normalization effects) does not change the CGT.
* Proposition (qualified): for |Phi>=L|Psi>/||L|Psi>||, differentiating the numerator gives (d_i L)|Psi> + L|d_i Psi>. The normalization derivative is parallel to |Phi> and is killed by the projective tangent projector, which proves invariance under nonzero scalar rescaling. The shorter expression containing only (d_i L)|Psi> is valid only when the input |Psi> is held fixed. Any bound for a lambda-dependent input must include ||L|d_i Psi>|| as well as ||(d_i L)|Psi>|| and a lower bound on ||L|Psi>||.

34.2 Convergence of discrete estimators

* Assumptions: (C1) Psi(lambda) is C2 on the patch; (C2) min-overlap between neighboring samples >= s_min > 0; (C3) rectangular stencils with step sizes delta_i -> 0.
* Result (sketch): The metric estimator using projected finite differences is first-order accurate: bias = O(max_i delta_i). The Wilson-plaquette curvature converges with bias O(max_i delta_i) and variance reduced by micro-plaquette averaging.

34.3 Pure vs mixed-state geometry: switching rule

* Use pure-state CGT only under declared overlap and coherence criteria, and report the criterion and estimator. The repository contains no tracked OEDI phase-noise sweep; the previously quoted `s_bar ~= 0.88` threshold came from illustrative CLI defaults and is not empirical evidence. A justified pure/mixed switch requires a raw-data manifest, a specified dephasing model, and a preregistered threshold or sensitivity analysis.

34.4 Physical interpretation of Psi

* Psi is a coherence-weighted occupancy field: |Psi_n|^2 equals the Q-layer occupancy share; arg Psi_n is the local phase clock derived from delays and Theta-couplings. Metric g measures susceptibility of this field to knob changes; curvature Omega measures holonomy of its phase-amplitude structure under loops in lambda. Observable consequences appear through edge currents and readout biases (see 34.7).

34.5 Causality and parameter-geometry

* Locality: the baseline transport kernel uses graph-local edges and delays. The full implementation also uses global normalization after active `geom_bias`, full-state Pancharatnam gauge fixing, a global-mean delay fallback for isolated nodes, centrality-derived susceptibility, and global readouts. The supported claim is local graph transport with potentially global estimation/control/readout; no stronger locality or signaling claim follows from the current code.

34.6 Control action (Section 6.1) motivation

* The postulated action S[lambda] = ∫(1/2 g_ij lambda_dot^i lambda_dot^j + A_i lambda_dot^i − U) has: (i) a schedule-dependent kinetic cost, (ii) a connection/gyroscopic term rather than ordinary work, and (iii) a potential term encoding objectives. The expression is coordinate covariant, but the quadratic kinetic term depends on schedule parameterization/timing. The closed-path connection contribution is gauge invariant under A_i -> A_i + d_i chi. Units, continuum scaling, and derivation from the discrete update remain open.

34.7 Why curvature biases amplitudes (mechanism)

* A scalar Berry connection increment A_i * Delta lambda^i produces only a common phase and cannot change edge phase differences. A nodewise field a_{i,n} could affect sinusoidal currents, but it requires a separately derived gauge-covariant decomposition/coupling; the repository has not derived one from the scalar connection. Even with such a coupling, response must be non-degenerate: benchmark C with `current_phase_gain=0` retains nonzero signed flux while excess-circulation response is exactly zero. The sign and magnitude therefore do not follow from Omega alone.

34.8 Choosing Xi_n by principle

* Principles: positivity, graph-isomorphism invariance, and minimal extra structure. The static choice (degree * eigenvector-centrality, normalized) is graph-global because eigenvector centrality depends on the whole graph; it is not a strictly local rule. Dynamic Xi is for feedback studies; learned Xi is for task optimization and must be ablated.

34.9 Conditional effect-size constant in R_anti ≈ kappa1 * Phi_gamma

* Conditional linear response: if response curvature aligns with CGT curvature, kappa1 = eta * sum_n (d log P_out / d M_n) * S_n is a possible coefficient decomposition, where S_n links memory response to flux. It is not derived or coefficient complete, and kappa1 can vanish. Report uncertainty from seeds and protocol choices, not only fit residuals.

34.10 Independent definitions of transitions (non-CGT)

* Q-only: spectral gap 1 − |lambda2(P)| of the Markov kernel P(lambda) approaching 0 indicates loss of mixing. Theta-only: Kuramoto order parameter r crossing a threshold indicates synchronization. Coupled: largest Floquet multiplier of the projective map crossing 1. Compare these to ridges in tr(g) to avoid circularity.

34.11 Sufficiency example for quantization (constructive)

* QP-1 is an $S^2$ sphere-chart Chern/flux calibration: `x` is periodic azimuth and each polar boundary collapses to a distinct north/south pole projector. It is not a two-periodic torus band, and its implemented eigenvalue gap varies with `y` while remaining open. The separate perturbed Qi–Wu–Zhang benchmark in `cwt/cgt/topology.py` is the repository's periodic-torus check.

34.12 Perturbation validity bounds

* Valid when || (d_i L) L^{†} || * loop diameter << spectral gap of L on the relevant invariant subspace, and when the FS distance per step is small (e.g., < 0.1 rad). Outside this, use the nonlinear diagnostics in Section 25.

34.13 Complexity scaling note

* Baseline cost O(N * T) (N nodes, T tiles). Refinement multiplies only a fraction f of tiles by <= 4^{r_max}. Publish (N, T, f, r_max, s_min, CI stop rules) so reviewers can assess computational feasibility.

## 35. Appendix QP-1: two-level $S^2$ Chern/flux calibration

QP-1 is a calibration of projector geometry and first-Chern flux over the sphere-coordinate quotient $S^2$, not a periodic-torus band benchmark.

Setup

* Parameters: `x` in `[0,1)` is a periodic azimuth and `y` in `[0,1]` is a polar coordinate. The projectors at `x=0` and `x=1` coincide; at each polar boundary the entire azimuthal circle collapses to one projector, with `y=0` and `y=1` giving distinct north/south poles. The quotient is $S^2$, not `T^2`.
* Step operator: the implementation uses a normal two-level map `L = V diag(mu1, mu2) V^-1`. Its dominant eigenvalue is one and its gap is `0.4 + 0.2 cos(2 pi y)`, so the gap varies from `0.2` to `0.6` but never closes.
* Right eigenvector:
  `u_R(x,y) = [cos(pi y/2), exp(i 2 pi x) sin(pi y/2)]^T`.
  For this normal construction `u_L=u_R`.

Curvature and integral

* With `A = -i u_L^† d u_R` and `Omega_xy = partial_x A_y - partial_y A_x`, one has `A_x = pi(1-cos(pi y))`, `A_y=0`, and `Omega_xy = -pi^2 sin(pi y)`.
* Integrating over the sphere-coordinate rectangle gives `integral Omega = -2 pi` in the repository convention. The analytic connection and Wilson plaquette estimator agree in magnitude and sign, and loop orientation reverses the flux.
* This verifies estimator normalization, sign, boundary handling, convergence, and the $S^2$ first-Chern value `C=-1` in the repository convention. The eigenvector gauge is patchwise/singular at a pole even though the projector is smooth. It does not establish a Chern number for a doubly periodic QP-1 band because QP-1 is not `T^2`.

### 35.1 Separate periodic-torus benchmark

The actual periodic `T^2` check is the perturbed Qi–Wu–Zhang lower-band benchmark implemented in `cwt-sim/cwt/cgt/topology.py`, with tracked output at `cwt-sim/cgt_benchmarks/results/benchmark_E_topology_torus/benchmark_e_topology.json`. Its topology claim is an auxiliary synthetic benchmark and should not be conflated with graph-derived or external-substrate evidence.

## 36. Active loop-response law and coefficient status

If an adiabatic/tangent-response reduction supplies $B^{(R)}$, the conditional Stokes identity is
\[
R_{\rm anti}(\gamma)=\oint_\gamma B^{(R)}+r_\gamma
=\int_{S_\gamma}dB^{(R)}+r_\gamma.
\]
Deriving that reduction and a deterministic or stochastic rate for $r_\gamma$ remains open for the unconstrained full CWT scheduler. Sections 36.2–36.4 separate the explicit benchmark-C fixed-tick recurrence, a general finite-dimensional uniformly contractive class theorem, and a named five-state core open-system specialization. The last item proves the reduction for one authored Benchmark D channel/readout, but still does not establish a physical-time scheduler law or an external response. For a specified shrinking-loop family with nonzero leading flux, the CGT law additionally requires non-degenerate coupling/readout, $r_\gamma=o(\Phi_\gamma)$, and $\int_{S_\gamma}(dB^{(R)}-\kappa_1\Omega)=o(\Phi_\gamma)$. Only then does $R_{\rm anti}=\kappa_1\Phi_\gamma+o(\Phi_\gamma)$, or $\Delta R_\gamma=2\kappa_1\Phi_\gamma+o(\Phi_\gamma)$. An evidentiary test must compute $\Phi_\gamma$ independently and measure a response whose definition contains no $\Phi$, $\Omega$, or loop orientation.

### 36.1 Evidence status

Current Gate A is a flux-conditioned construction check because signed flux is passed into `memory_current_coupled` and then into the readout. The post-hoc OEDI reconstruction did not run a loop response and refutes the prior sign-boundary interpretation; its separately frozen passive protocol was executed and failed, but it is a distance/dissimilarity diagnostic rather than an active-response test. Chicago has no tracked quantitative payload result. The alignment law is therefore an open hypothesis, not an externally supported shape law. Benchmark C with `current_phase_gain=0` also proves that a nonzero flux can coexist with \(\kappa_1=0\).

### 36.2 Narrow benchmark-C fixed-tick theorem

The executable harness at `cwt-sim/experiments/independent_response_theorem/` isolates the existing benchmark-C circulation readout from its geometric predictors. It preserves the legacy mean response and additionally defines
\[
q_t=C(p_t,\theta_t^{\rm actual},K_t)-C(p_t,\theta_t^{\rm branch},K_t),
\qquad
Q=\sum_t q_t,
\qquad
Q_{\rm anti}=\frac{Q_{\rm CCW}-Q_{\rm CW}}{2}.
\]
Here $Q$ is only a `discrete_cycle_sum_surrogate` in circulation-current-ticks with `dt=1`; it is not transported charge. With fixed per-tick relaxation $\alpha$ and $q=1-\alpha$, the no-wrap phase error $e_t=\theta_t^{\rm actual}-\theta_t^{\rm branch}$ obeys the exact recurrence
\[
e_t=q e_{t-1}-q\,\Delta\theta_t.
\]
For the fixed C0 branch and a uniformly sampled piecewise-smooth loop, bounded branch derivatives and the stable recurrence give $e_t=O(1/m)$. Taylor expanding the same circulation observable and summing the finitely many start/corner transients gives
\[
Q=\oint_\gamma B_i^{(R)}d\lambda^i+O(1/m),
\qquad
B_i^{(R)}=-\frac{1-\alpha}{\alpha}\,\nabla_\theta C\cdot\partial_i\theta.
\]
This is a theorem for that explicit fixed-tick recurrence under the locked fixed-branch/no-wrap assumptions, not for arbitrary CWT history dependence. Increasing $m$ lengthens and slows the discrete cycle. Because the off-center initialization remainder is $O(s/m)$ while the loop signal is $O(s^2)$, the shrinking-side check couples the refinement as $m\propto s^{-2}$; fixed $m$ would not establish the area limit.

The locked deterministic run separately computes $F_R=\partial_uB_v-\partial_vB_u$, projective $\Omega=2\,\mathrm{Im}\langle D_u\Psi|D_v\Psi\rangle$, and Wilson flux after calculating the response. At center $(0,0)$ it finds $F_R=-0.079351069$, $\Omega=0.145833318$, and the local two-form quotient $F_R/\Omega=-0.544121672$. The legacy mean decays with log-slope $-1.0105$, the summed line-remainder scales with log-slope $-0.9579$, and the finest $Q_{\rm anti}/A$ and $\Phi_{\rm anti}/A$ relative errors are $2.47\times10^{-4}$ and $2.13\times10^{-6}$. The maximum finite-loop/local-quotient consistency error over four centers is $0.3012\%$, while the quotient varies from approximately $-0.7363$ to $-0.3434$.

This quotient comparison has no independent CGT-predictive content. On a two-dimensional parameter chart, any two nonzero 2-forms are pointwise proportional, so $F_R/\Omega$ exists algebraically wherever $\Omega\ne0$, and $Q_{\rm anti}/\Phi_{\rm anti}\to F_R/\Omega$ follows when the two separately checked area limits converge. The comparison is useful only as an implementation-consistency check. Its variation across centers rules out treating it as one common coefficient but does not itself validate a response law. The exact same-observable controls `current_phase_gain=0` and `phase_relaxation=1` give zero response to floating precision.

The estimand and thresholds were selected after an exploratory center-$(0,0)$ square refinement probe; all benchmark-C configurations are discovery/analytic fixtures. The run has no seeds or uncertainty interval and is neither preregistered nor an untouched holdout. Its response calculator receives no $\Phi$, $\Omega$, signed area, or orientation metadata, but the synthetic state/readout family remains authored. See `PROTOCOL_LOCK.md`, strict JSON records/provenance, and the generated report in that experiment. This closes a narrow analytic precursor only; the central empirical/external alignment claim remains proof incomplete.

### 36.3 Uniform-contraction class theorem and exact alignment no-go

The executable proof program at `cwt-sim/experiments/response_theorem_proof_program/` treats a finite-dimensional right-endpoint update-then-sample system
\[
x_n=F_c(x_{n-1},\lambda_n),\qquad Q_c=\sum_{n=1}^N r_c(x_n,\lambda_n).
\]
Assume a `C3` compact tube, a smooth fixed branch $\bar x_c$, centered readout, one fixed norm with $\|D_xF_c\|\le\rho<1$ uniformly, a closed piecewise-`C2` exact-reverse path, and equilibrium error $O(1/N)$. With
\[
M_c=D_xF_c,\quad H_c=D_xr_c,\quad X_{c,i}=\partial_i\bar x_c,
\quad B_{c,i}=-H_c(I-M_c)^{-1}M_cX_{c,i},
\]
the contraction/summation argument gives
\[
Q_c=\oint_\gamma B_c+O(N^{-1}).
\]
Consequently the complete on/zero interaction obeys
\[
D=Q_{{\rm anti,on}}-Q_{{\rm anti},0}
=\oint_\gamma(B_{\rm on}-B_0)+O(N^{-1})
=\int_S d(B_{\rm on}-B_0)+O(N^{-1}),
\]
and the ordinary difference-in-differences is $2D$. No $B_0=0$ assumption is made. For a loop of scale $s$, the generic equilibrium-reset bound is $C_1s/N+C_2s^2/N$, so area-relative convergence requires $Ns\to\infty$. The stronger $C'_1s^2/N+C'_2s/N^2$ bound requires a unique driven periodic orbit or matched corrector, endpoint-consistent full-period sampling, a periodic/endpoint-flat `C3` loop and branch, and a proved summation-by-parts cancellation. It cannot be inferred from smoothness alone.

The continuous-time corollary separately requires both (i) uniform frozen-branch hyperbolicity/invertibility, $\sup_{c,\lambda}\|J_c(\lambda)^{-1}\|\le K_J<\infty$, and (ii) a uniform bound $\|U_c(t,u)\|\le M e^{-(t-u)/\tau}$ on the propagator of the branch-linearized equation along every declared slow-$T$ loop family, all in one common norm. Pointwise Hurwitz matrices are insufficient, and the driven-propagator bound alone does not imply the frozen inverse bound: $f(x,\lambda)=(-1+\lambda)(x-\lambda)$ along $\lambda(t)=\sin t$ has $|U(t,u)|\le e^2e^{-(t-u)}$ while $J=0$ at $t=\pi/2$. Here $Q_c=\int_0^T r_c(x(t),\lambda(t))\,dt$; the generic result uses equilibrium initialization, while the stronger result uses a unique driven-periodic orbit or proved matched corrector, exact reversal $\lambda_-(t)=\lambda_+(T-t)$, and one endpoint/quadrature convention. Its generic remainder is $O(s\tau/T)$ and its separately justified periodic improvement is $O(s^2\tau/T+s(\tau/T)^2)$. This is not a derived continuum limit of CWT.

The same program proves an exact realizability/no-go result. For any smooth one-form $\beta$ and $0<\rho<1$,
\[
x_n=\rho x_{n-1}+(1-\rho)\lambda_n,
\qquad
r=-\frac{1-\rho}{\rho}\,\beta(\lambda)\cdot(x-\lambda)
\]
realizes $B=\beta$ exactly. A normalized projective state map, and hence its $\Omega$, can be chosen independently in an augmented contracting state. Therefore contraction, smoothness, a gap, and a branch imply neither $\Omega\ne0\Rightarrow F_R\ne0$ nor $F_R\ne0\Rightarrow\Omega\ne0$, and cannot imply $F_R^D=\kappa\Omega$. Alignment additionally requires zero-set compatibility, collinearity, and $d\kappa\wedge\Omega=0$; a pointwise quotient remains tautological in two dimensions. The computed C1–C8/P1 matrix includes non-implications, sign-changing/readout-dependent coefficients, finite-speed effects, covariance checks, a scoped non-normal warning, and a three-dimensional deliberately aligned oracle/positive implementation control. P1 is not an independently measured response. Its disposition is `PASS_INTERNAL_ANALYTIC` / `NO_EMPIRICAL_EVIDENCE`; numerical fixtures test the implementation rather than prove the theorem or support an external response law. Benchmark C in Section 36.2 is a narrow linear-contracting corollary under its locked assumptions.

### 36.4 Named Benchmark D core open-system specialization

The executable harness at `cwt-sim/experiments/benchmark_d_open_response_proof/` instantiates the contraction theorem with the named core map `cwt.cgt.open_system.apply_local_open_step`, the fixed Benchmark D `D0` kernel, and the geometry-blind Hermitian `mean_position` readout. It freezes

* $b\in[0.01,0.05]$, $d\in[0.205,0.245]$, centered at $(0.03,0.225)$;
* `dt=.18`, edge-jump scale `.20`, depolarization `.008=1/125`, dephasing `.30`, and zero coherent/site-potential scales;
* a single fixed branch with no continuation; and
* right-endpoint update-then-sample $Q=\sum_n H[x_n-\bar x(\lambda_n)]$, with CW the exact stored-sequence reverse.

On the invariant diagonal-density subspace the core Kraus map reduces exactly to
\[
x_n=M(b_n,d_n)x_{n-1}+c,
\qquad
M=\frac{124}{125}\left[\left(1-\frac9{250}\right)I+\frac9{250}K(b,d)\right]^T,
\qquad c=\frac1{625}{\bf 1}.
\]
The true fixed branch is $\bar x=(I-M)^{-1}c$. Exact Kraus completeness, inactive clip/rescale/square-root thresholds, a full-rank depolarizing floor, and the global trace/$\ell^1$ contraction factor $124/125$ are certified on the box. The experiment-local affine reduction is cross-checked against complete cycles of the core function; it does not use the authored `stationary_from_row_stochastic` vector as the open-system fixed point.

For $H=(1,2,3,4,5)$, exact rational implicit differentiation of
\[
B_i=-H(I-M)^{-1}M\partial_i\bar x
\]
at the center gives
\[
F_{bd}=\partial_bB_d-\partial_dB_b
=-\frac{1389405980846240823998759336989273383099794763750000000000}
{2559023550169319630994375590863181495045970285707766901}
\approx-542.9438039967665.
\]
An independent numerical curl agrees, the fixed-loop error converges as $O(1/N)$, and an in-box shrinking-square ladder with $Ns\to\infty$ gives $Q_{\rm anti}/s^2\to F_{bd}$. Its tolerances were selected during internal harness development and are regression checks, not preregistered evidence; an explicit fixed-solver centering budget is negligible relative to the observed convergence error. Identity-readout and constant-branch controls vanish; depolarization zero is refused a strict contraction certificate; and Benchmark C's true unital fixed branch gives zero centered response.

This is `PASS_INTERNAL_ANALYTIC` / `NO_EMPIRICAL_EVIDENCE` for one authored five-state fixed-tick core channel/readout. It is not the full scheduler, a physical-time model, an external result, or a CGT alignment law. The authored stationary-probability D0 geometry is not used as a smooth projective branch. Instead, because the frozen channel is insensitive to $p$ and $\theta$, a separately frozen constant normalized reference $p_j=1/5$, $\theta_j=0$ has exactly $\Omega_{bd}=0$. Its coexistence with nonzero response curvature is only a constant-reference no-go control: response curvature does not by itself imply universal CGT alignment. The historical Phase10 entry script explicitly selects `branch_steps=2`, and the tracked Benchmark-C JSON records that value plus recommended $\gamma=0.2$; the current library default is 3 and `cwt/cgt/analysis/phase10_analysis.py` is the current recomputation implementation. Recomputing from the explicit recorded configuration gives a nonzero fixed residual, so the artifact remains a finite-step surrogate. A separate Benchmark-D three-step diagnostic does not validate that historical artifact.

### 36.5 Current coefficient decomposition is approximate

The earlier scalar decomposition
\[
\kappa_1 \approx \eta\,\bar{s}\,G_\theta\,\kappa_{\rm loc}
\]
is a heuristic scaling ansatz, not a coefficient-complete prediction. Moreover, every positive scalar multiplier applied uniformly inside the current column-normalized transport construction cancels under normalization; `kappa=0` instead triggers the degenerate identity/self-loop fallback. Neither case implements directional anisotropy. The ansatz therefore neither predicts the leading shape nor the absolute coefficient without a concrete non-cancelling mechanism.

### 36.6 Coefficient-complete direction

A coefficient-complete theory should derive \(\kappa_1\) from branch-local tangent or adjoint response. Let \(x_t=(p_t,\theta_t)\) and let \(U(T,t+1)\) be the tangent propagator from step \(t+1\) to the final time. If \(B_i(x_t,\lambda_t)\Delta\lambda_t^i\) is the infinitesimal phase-kick/control perturbation at step \(t\), then
\[
\delta x_T = \sum_t U(T,t+1)B_i(x_t,\lambda_t)\Delta\lambda_t^i,
\]
\[
\delta R = \nabla R(x_T)\cdot \delta x_T.
\]
The coefficient \(\kappa_1\) should be the coefficient of \(\Phi_\gamma\) in this adjoint response. This formulation naturally includes graph size, edge normalization, path length, readout sensitivity, phase-field amplitude, and substrate-specific transport amplification.

## 37. Complexity classes for feasibility

We group experiments by (N nodes, T tiles, f refined fraction, r_max refinement depth):

* Class A (workstation-ready): N ≤ 1e3, T ≤ 1e3, f ≤ 0.1, r_max ≤ 2.
* Class B (multi-core/GPU helpful): N ≤ 1e4, T ≤ 5e3, f ≤ 0.2, r_max ≤ 3.
* Class C (cluster recommended): up to N ~ 1e5, T ~ 1e4, or f ≥ 0.3 with r_max ≥ 3.
  Report (N, T, f, r_max, s_min, CI tolerance) with results; this lets users gauge feasibility up front.

## 38. Minimal complete example: 3-node ring

Graph

* Nodes {0,1,2} with directed cycle 0→1→2→0 and symmetric weights. Delays set a base phase clock; Theta coupling nearest-neighbor.
  Parameter manifold and loop
* Use lambda = (rho, tau). Drive a small rectangular loop around (rho0, tau0) in the adiabatic regime.
  Pipeline

1. Build Psi at each corner by combining Q amplitudes and Theta phases; normalize.
2. Compute theta_geo (thermometer) to confirm moderate sensitivity; then compute metric g and curvature Omega via stable plaquettes.
3. Run the loop twice (CW/CCW). A current-coupled memory readout that directly receives flux may be used only as a construction check; use a flux-independent readout for validation.
4. Test orientation-odd response and an area ladder. Test proportionality to Phi_gamma only as a separate alignment hypothesis, including the `current_phase_gain=0` nondegeneracy control.
5. Independently compute Kuramoto order parameter r and Markov spectral gap to locate the synchronization/mixing transition. Compare to ridges in tr(g).
   Expected outcomes

* Hypothesis to test: an independently defined synchronization transition may co-locate with a tr(g) ridge, and an independent loop readout may have nonzero orientation-odd response nearby. Null ridge, null response, or zero `kappa_1` outcomes are admissible.

## 39. Failure modes and caveats

* Numerical: small overlaps (instability), gauge singularities near EPs, CI caps hit frequently on rough landscapes.
* Estimator: direct-neighbor settling may drift between adjacent parameter samples, mixing incomplete relaxation or continuation history into finite differences and Wilson tiles. Require settling-convergence and path-consistency checks.
* Physical: dynamic Xi feedback can destabilize unless contraction safeguards are used; C-layer saturation (T→0 or thresholds too low) can mask geometric effects.
* Regime: non-adiabatic driving (large FS jumps) invalidates linear scaling; heavy disorder that closes gaps breaks topological plateaus.
* Interpretive: using CGT to both define and detect “criticality” is circular; rely on independent criteria (Section 34.10).
* Validation: several late "holdout" phases, including 221/222, load pre-baked summary JSON that was adaptively reused across phases. These artifacts are descriptive regression fixtures, not reproducible independent holdouts.
* Locality/control: scalar transport factors can cancel under column normalization, directional anisotropy is not implemented in that path, and several estimation/control/readout operations are global.

## 40. Baselines and ablations

The active loop-response layer must be compared against preregistered models that do not use oriented curvature. A specified metric-only scalar surrogate predicts no orientation-antisymmetric response:
\[
R_{\rm anti}=\frac{R_{\rm CCW}-R_{\rm CW}}{2}=0.
\]
The helper `metric_only_null_rejection` tests only a supplied linear-correlation surrogate and cannot reject the general orientation-null family; degenerate metric or response inputs are indeterminate. No tracked OEDI or Chicago artifact rejects an external orientation-null model.

The passive transition-ridge layer should be compared against Q-only baselines such as non-degenerate spectral gap, mixing time, and second singular value of the transport kernel. Labels and thresholds must be defined ex ante and evaluated on spatially blocked or substrate-held-out data. Current internal Gate B labels are post-hoc grid percentiles, while tracked OEDI/Chicago artifacts do not provide this comparison.

Ablation reports must distinguish:

1. active orientation-null baselines,
2. passive transition-ridge baselines,
3. estimator sign/gauge checks,
4. seed/init variability,
5. geometry scrambles of the connection and curvature channels.

## 41. Conjectural geometric universality classes (GUC)

The following is a proposed taxonomy for future tests, not an empirically established classification.

Criteria

* Symmetry of transport and coupling: reversibility of K, symmetry of J, presence of frustration or chirality.
* Graph ensemble invariants: degree distribution shape, clustering, modularity, spectral gap scaling with size.
* CGT critical exponents: scaling of tr(g) and |Omega| near a gap closing; codimension of exceptional points.
* Topological sector: first-Chern index C on a closed oriented parameter surface with a smooth gapped projector.

Class examples

* GUC-A hypothesis: reversible kernels on expander-like graphs with weak Theta coupling may show sharp metric ridges and small curvature away from selected loops.
* GUC-B hypothesis: chiral or genuinely anisotropic transport with moderate coherence may show robust nonzero curvature; a pumpable readout still requires an independent non-degenerate coupling and alignment.
* GUC-C hypothesis: modular graphs with weak inter-module edges may show multiple ridges and module-dependent geometric structure.

Predictions

* Test whether normalized ridge shapes collapse after rescaling by independently specified gap/thermometer variables, and separately test response scaling with an independent readout. Null collapse and null response remain admissible.

## 42. Inverse design via CGT

Goal: choose a graph and a parameter schedule to achieve a target macroscopic effect.

Objectives

* Maximize pumped bias toward a target region or outcome set.
* Minimize control effort measured by the metric term along the path.
* Keep dynamics within a gapped, stable regime to avoid breakdown.

Design program

1. Outer loop: edit graph weights under constraints (nonnegative, degree or budget preserved).
2. Inner loop: optimize a closed path in parameter space to achieve a target flux while keeping thermometer and overlap within limits.
3. Sensitivities: use gradients of readout with respect to memory terms and local currents, and use tr(g) as a control cost proxy.
4. Open requirement: demonstrate a non-degenerate, independently measured response and response-curvature alignment. Nonzero loop flux in a gapped sector does not by itself imply nonzero bias or fix its sign.

## 43. Noise and coherence robustness

Noise robustness is an open empirical obligation. The tracked repository does not contain an OEDI Gate A noise sweep; the previously reported `s_bar ~= 0.88` sign threshold is reproduced only by illustrative hand-entered CLI defaults and must not be cited as external evidence. A valid study should preserve a raw-data manifest and report phase-noise scale, final coherence, maximum Fubini–Study step, adiabatic validity, seed variability, and whether the response is independent of both the coherence measure and CGT flux.

## 44. Linking CGT to emergent phenomena

Mapping

* Synchronization transition: rapid rise in Kuramoto order r may co-locate with a ridge in tr(g) in an overlap-safe, transition-localized regime. This remains an internal synthetic hypothesis; tracked OEDI and Chicago artifacts do not validate the co-location claim.
* Pattern selection and fronts (conditional design hypothesis): a separately implemented gauge-covariant coupling may translate persistent Omega sign structure into front bias; CGT geometry alone does not select a pattern.
* Rectified transport (conditional design hypothesis): nonzero Omega plus an implemented, non-cancelling directional anisotropy may create directional flows under cyclic control. Positive values of the current uniform scalar `kappa` cancel under column normalization; zero triggers a degenerate self-loop fallback. Neither establishes anisotropy or rectification.

## 45. Modeling real systems as graphs

Guidelines

* Nodes represent local state holders (oscillators, buses, servers, cells). Edges carry flow with weights from coupling strength or capacity. Delays encode processing, transmission, or reaction lags.
* Q layer comes from occupancy, load, or probability of activity; Theta from phase-like clocks (swing phase, rotation, signal phase, reaction phase).
* Parameter manifold examples: density and delay scale; coupling gain; anisotropy; external field strength.
  Examples
* Power distribution feeders with load-dependent delays and phase angles: candidate domain for testing whether an independent seasonal-loop response aligns with CGT flux.
* Neural microcircuits with local oscillations: candidate domain for testing a preregistered, gauge-covariant response coupling under slow neuromodulatory cycles.
* Traffic or logistics networks with congestion-induced delays: candidate domain for testing, not assuming, directional loop response and bottleneck effects.

## 46. Timescale separation criteria

* Graph timescale: characteristic propagation and phase-locking time from local delays and coupling.
* Control timescale: time to traverse a loop segment in parameter space.
* A small average Fubini–Study step and small control-speed/gap ratio are heuristic diagnostics. The current `0.1` step threshold is a declared engineering rule, not a derived universal boundary.

## 47. Orientation reversal: first-order argument

If an adiabatic/tangent-response reduction gives a leading local line functional under small, slow loops, Stokes' theorem makes its orientation-odd half-difference the surface integral of response curvature, which reverses sign with loop orientation. Deriving that reduction for CWT is open. Identifying response curvature with CGT curvature requires the separate alignment/nondegeneracy hypothesis. Higher-order corrections appear at larger loop size or near non-adiabatic regimes.

## 48. Representation invariance of predictions

Two representations that yield the same projective state produce identical CGT and closed-loop flux. Equality of any actuated or pumped readout additionally requires an explicitly gauge-covariant control/readout map; that construction is open for the proposed nodewise phase-kick mechanism.

## 49. Candidate application domains

* Power grids and microgrids; delays from frequency and dispatch constraints.
* Neuronal populations and oscillatory circuits; delays from synaptic and conduction latencies.
* Swarm and robotic coordination; phase-like headings, delays from communication and actuation.
* Queues and microservices; occupancy and backpressure set delays and phases.
* Chemical or ecological networks; reaction or migration delays.

## 50. Empirical roadmap beyond toy models

* Validate QP-1 and the 3 node ring. Then scale to an externally sourced dataset with documented observation lineage in one domain above.
* Show advantage over metric-only and spectral-only baselines on hotspot prediction and directional bias calibration.
* Publish full auditing tuple (N, T, f, r_max, s_min, CI rules) and preregistered hypotheses.

## Current empirical status

Current tracked evidence supports the following ranking.

**Analytic/executable support:** CGT metric/Wilson estimator identities and sign convention; QP-1 $S^2$ Chern/flux magnitude, sign, quotient-boundary behavior, and open varying gap; a separate synthetic Qi–Wu–Zhang periodic-torus check; the benchmark-C `current_phase_gain=0` nondegeneracy counterexample; the locked benchmark-C fixed-tick theorem $Q=\oint B^{(R)}+O(1/m)$; and the finite-dimensional uniform-contraction theorem $Q_c=\oint B_c+O(1/N)$ with its exact arbitrary-one-form realizability/no-go result. The contraction theorem supplies a response one-form for its declared class but also proves that smooth contraction alone cannot align response curvature with independently chosen projective $\Omega$. It has authored counterexamples and a three-dimensional deliberately aligned oracle/positive implementation control only: `PASS_INTERNAL_ANALYTIC` / `NO_EMPIRICAL_EVIDENCE`. The benchmark-C item remains a selected internal discovery/analytic corollary, not independent empirical validation, a physical-time result, or external evidence; its $F_R/\Omega$ comparison is only a tautological 2D quotient/implementation-consistency check.

**Internal exploratory support only:** synthetic Gate A construction consistency, synthetic Gate B same-grid co-location behavior, and synthetic Gate C loop/noise robustness. Gate A and Gate C inject flux into memory/readout. Gate B uses post-hoc percentile labels and non-spatial cell bootstrap. Gate C's threshold boolean is not a Chern/topology result. Late summary-JSON "holdouts" are adaptive/pre-baked rather than independently reproducible.

**Provenance-locked OEDI reconstruction and failed auxiliary passive diagnostic, no positive theory evidence:** OEDI's archived vector is reproducible from a pinned official test-system source consistent with it, but original historical provenance is unproven and the corrected analysis refutes the old structural/sign-boundary interpretation. The separately frozen 61-profile same-package confirmation then failed: $T=0.013066368743938832<0.10$, $p=0.39696$ with 99% Clopper-Pearson Monte Carlo interval for the permutation-tail probability $[0.39296862162223856,0.4009491374352013]$, and leave-one/lateral sign stability failed despite 77/77 admitted files passing QC. This fails to reject the conditional bus-bundle random-label null and supplies no support for the prespecified auxiliary locality diagnostic; it does not prove exact absence or validate/falsify CGT/CWT. Chicago remains endpoint/schema metadata only.

**Open:** proving that a concrete non-toy CWT update satisfies the uniform contraction/smooth-branch hypotheses; any independently predictive or externally validated CGT-flux/readout alignment; any universal or externally nonzero \(\kappa_1\); external passive ridge prediction; general orientation-null rejection; noise threshold/robustness; direct \(\Omega\)-bias actuation; a derived continuous-time CWT limit/action with units; and full-stack locality.

See `cwt-sim/cgt_benchmarks/reports/CWT-CGT_Proof_Status_v1.md` for the claim/evidence/proof-obligation matrix.
