**Author:** Dave Medeiros / Panoptic Systems

---

## 1. Scope & Motivation

Causal Web Theory (CWT) posits that observed dynamics emerge from strictly local propagation on a graph substrate with density-dependent delays. Three interacting layers capture distinct aspects of evolution:

* **Q-layer**: stochastic amplitude flow (probability mass on nodes/edges),
* **Θ-layer**: phase/coherence field that steers interference-like behavior,
* **C-layer**: classicalization/readout producing macroscopic outcomes.

We “bake in” a geometry on the **space of control parameters** that govern the substrate and layer couplings. This geometry is encoded by a **CWT Geometric Tensor (CGT)**, directly analogous to the Quantum Geometric Tensor (QGT): its **real** part is a sensitivity **metric** and its **imaginary** part is a **Berry-like curvature** that imparts path-dependent biases. The CGT lets CWT formalize criticality, adiabatic pumping, and topological sectors of causal propagation—without introducing extra hidden variables outside the model’s state.

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

For a chosen analysis time/window and **control parameters** $\lambda\in\mathcal{M}$, define the normalized complex field

$$
\Psi_n(\lambda)=\sqrt{p^{(Q)}_n(\lambda)}\,e^{\,i\,\theta^{(\Theta)}_n(\lambda)},\qquad \sum_n |\Psi_n|^2=1.
$$

Gauge freedom: $\Psi\to e^{i\phi(\lambda)}\Psi$ leaves observables below invariant.

### 2.4 Control/Parameter Manifold

The **parameter manifold** $\mathcal{M}$ contains slow knobs that shape kernels and couplings. Minimally:

$$
\lambda = (\rho,\tau),\quad \text{optionally}\quad (\rho,\tau,\zeta,\kappa,\ldots)
$$

* $\rho$: mean occupancy or injection density,
* $\tau$: density-dependent delay scale, $\tau\!=\!\tau(\rho)$ allowed,
* $\zeta$: Q–Θ coupling strength (phase-amplitude feedback),
* $\kappa$: anisotropy/resistance of directed transport.

---

## 3. Axioms

**A1 (Locality on $G$).** Propagation per time step uses only local neighborhoods in $G$, with delays $\tau_{nm}$ and weights $w_{nm}$.

**A2 (Dual Fields & Normalization).** Each analysis slice induces a unique $\Psi=\sqrt{p^{(Q)}}e^{i\theta^{(\Theta)}}$ up to gauge, with $\|\Psi\|=1$.

**A3 (Geometric Control).** Geometry of $\Psi(\lambda)$ on $\mathcal{M}$ constrains evolution: the CGT’s real part measures sensitivity; its imaginary part generates anholonomy that persists into C-layer readouts.

**A4 (Topological Sectors).** Nontrivial curvature flux over closed 2-surfaces in $\mathcal{M}$ defines topological phases of causal propagation with loop-invariant macroscopic signatures.

**A5 (Classicalization).** Readout maps $F$ from $(p^{(Q)},\theta^{(\Theta)})$ to outcomes are allowed to depend on the **path** taken in $\mathcal{M}$ via geometric quantities.

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

The connection form $\mathcal{A}_i=i\langle\Psi|\partial_i\Psi\rangle$ satisfies $\Omega_{ij}=\partial_i\mathcal{A}_j-\partial_j\mathcal{A}_i$.

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

### 5.3 Geometric Couplings

**(a) Geometric phase kick along parameter path)**
For a small parameter step $\Delta\lambda$:

$$
\theta^{(\Theta)}_n \;\mathrel{+}=\; \mathcal{A}_i(\lambda)_n\,\Delta\lambda^i.
$$

**(b) Curvature-induced transverse bias in Q)**
Treat curvature as a magnetic-like 2-form on $\mathcal{M}$ that deflects probability flow when $\lambda$ moves:

$$
\boxed{\; \Gamma_n = \beta\,\sum_{i<j}\Omega_{ij}(\lambda)\,\epsilon^{ij}\,\Xi_n\;}
$$

* $\epsilon^{ij}\,$ contracts with the oriented area swept by the parameter step (or $\dot\lambda^i$ in continuous time),
* $\Xi_n$ is a nodewise susceptibility (e.g., degree-normalized centrality, or learned from metrics),
* $\beta$ is a coupling coefficient.

Apply to the Q update as an additive pre-normalization term:

$$
\tilde p^{(Q)}_n(s+1) \;\mathrel{+}=\; \alpha\,\Gamma_n,\quad \text{then renormalize.}
$$

$\alpha$ sets the amplitude of geometric bias.

### 5.4 Conservation & Stability

* Ensure $\sum_n p^{(Q)}_n=1$ each step.
* Clip geometric additions if needed to keep $\tilde p^{(Q)}_n\ge 0$ before normalization.
* Use phase unwrapping and small $|\Delta\lambda|$ to maintain numerical stability of $\mathcal{A},\Omega$.

### 5.5 Operator Form (Optional)

Define an effective one-step map $U(\lambda)$ (or generator $H_\mathrm{eff}$) acting on $\Psi$. Band-resolving $U$ in a graph-spectral basis allows bandwise CGT, topological indices, and mode-selective analysis.

---

## 6. Control on the Parameter Manifold

### 6.1 Action for Schedules

When the experimenter or scheduler controls $\lambda(s)$, assign an action

$$
S[\lambda]=\int ds\,\Big(\tfrac{1}{2}g_{ij}(\lambda)\,\dot\lambda^i\dot\lambda^j + \mathcal{A}_i(\lambda)\,\dot\lambda^i - U(\lambda;G)\Big).
$$

* The **metric term** penalizes fast moves where the system is sensitive.
* The **Berry term** captures work due to curvature (“magnetic” deflection in parameter space).
* $U$ encodes objectives/constraints (e.g., holding density ranges, energy budgets).

Euler–Lagrange yields geodesic-plus-Lorentz equations on $\mathcal{M}$:

$$
\frac{d}{ds}\Big(g_{ij}\dot\lambda^j+\mathcal{A}_i\Big)-\tfrac{1}{2}\partial_i g_{jk}\,\dot\lambda^j\dot\lambda^k - (\partial_i\mathcal{A}_j)\,\dot\lambda^j + \partial_i U=0.
$$

This can drive **auto-schedulers** that choose smooth loops to probe curvature while avoiding high-$g$ ridges.

---

## 7. Observables & Phases

### 7.1 Geometry Observables

* **Metric scalars:** $\mathrm{tr}\,g$, $\sqrt{\det g}$. Large values flag critical sensitivity.
* **Curvature density:** $|\Omega_{ij}|$ and its sign.
* **Loop flux:** $\Phi_\gamma=\oint_\gamma \mathcal{A}_i\,d\lambda^i=\tfrac{1}{2}\iint_\Sigma\Omega_{ij}\,d\lambda^i\wedge d\lambda^j$.
* **Topological index (on toroidal $\mathcal{M}$):** $C=\frac{1}{2\pi}\int_{\mathcal{T}^2}\Omega\in\mathbb{Z}$.

### 7.2 Readout/Response Observables

Define a pumped-bias observable from C-layer outcome probabilities under a closed loop $\gamma$:

$$
\mathcal{R}_\gamma = \sum_X w_X\Big(P_X^{\,\circlearrowleft}-P_X^{\,\circlearrowright}\Big),
$$

with weights $w_X$ to target specific outcomes. Expect $\mathcal{R}_\gamma\propto \Phi_\gamma$ for small loops.

### 7.3 Phase Structure

* **Critical frontiers:** ridges in $\mathrm{tr}\,g$ and peaks in $|\Omega|$.
* **Topological plateaus:** integral curvature invariant to small noise in $\lambda$-loops.
* **Order ↔ disorder regions:** inferred from long-time variance of $p^{(Q)}$ and phase locking of $\theta^{(\Theta)}$.

---

## 8. Validation Gates (Theory-Level Tests)

**Gate A — Density–Delay Loop.** Drive a rectangular loop in $(\rho,\tau)$. Measure $\Phi_\gamma$ and $\mathcal{R}_\gamma$. Verify proportionality and orientation reversal.

**Gate B — Critical Ridge Finder.** Grid-scan $(\rho,\tau)$; compute $\mathrm{tr}\,g$ and $|\Omega|$. Promote tiles with large scores for high-fidelity runs.

**Gate C — Topology Robustness.** Add noise to $\lambda$ during loops. Check that $\Phi_\gamma$ and $\mathcal{R}_\gamma$ persist up to a threshold, indicating topological protection.

**Gate D — Bell/CHSH Modulation (optional).** If a CHSH gate exists, correlate deviations in correlators with $|\Omega|$ along small loops.

---

## 9. Limiting Cases & Consistency

* **Static parameters:** $\partial_i\Psi=0\Rightarrow g=0,\Omega=0$; CWT reduces to baseline local dynamics.
* **Phase-randomized regime:** dephasing $\theta$ $\Rightarrow \Omega\to 0$ (no coherent path memory).
* **Uniform amplitudes:** $p$ flat $\Rightarrow g\to 0$ (insensitivity to small parameter changes).
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
* **Adiabatic Pumps/Thouless Pump:** Curvature-induced pumping in $\mathcal{M}$ leads to directional biases in C-layer outcomes, analogous to quantized transport under parameter cycles.

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
2. Run the system; at each step, build $\Psi$, apply $\mathcal{A}\Delta\lambda$ to phases and $\Gamma$ to amplitudes.
3. After the loop, compute $\Phi_\gamma$ via Wilson loop and measure $\mathcal{R}_\gamma$ from C-layer outcomes.
4. Reverse loop orientation; confirm sign flip in $\Phi_\gamma$ and $\mathcal{R}_\gamma$.

---

## 14. Falsifiable Predictions

* Small parameter loops produce linear pumped biases $\mathcal{R}_\gamma\propto\Phi_\gamma$ with orientation reversal.
* Ridges of $\mathrm{tr}\,g$ co-locate with previously observed critical transitions in Q/Θ behavior.
* On a toroidal $\mathcal{M}$, integrated curvature attains integer-like plateaus under disorder up to a threshold.

---

## 15. Closing Remarks

The CGT integrates seamlessly with CWT’s localist ontology: it reframes how **control** shapes **emergence** via intrinsic geometry on parameter space. This unifies sensitivity analysis, adiabatic memory, and topological robustness under one mathematical roof—while keeping all dynamics strictly local on $G$.

---

## 16. Analytic Operator Form (Expanded)

We formalize three complementary operator views that enable spectral analysis, eigenstate geometry, and perturbation theory.

### 16.1 Non-Hermitian Linear Map (Projective Dynamics)

Define a step operator L(lambda) in C^{N x N} acting on Psi such that

|Psi'⟩ = L(lambda) |Psi⟩ / || L(lambda) |Psi⟩ ||.

• Interpretation: transport + delay + coherence packed into a single linear (generally non-unitary) map, followed by projective normalization.

• Biorthogonal spectrum: right/left eigenpairs L |u_a^R⟩ = mu_a |u_a^R⟩, ⟨u_a^L| L = mu_a ⟨u_a^L|, with ⟨u_a^L|u_b^R⟩ = delta_ab.

• Critical ridges: crossings and exceptional points (non-diagonalizable L) correlate with spikes in tr(g) and |Omega|.

• Eigenstate geometry: define biorthogonal connection A_i^(a) = i ⟨u_a^L| ∂_i u_a^R⟩ and curvature Omega_ij^(a) = ∂_i A_j^(a) − ∂_j A_i^(a). On a toroidal parameter manifold, C_a = (1/2pi) ∫ Omega^(a) is integer-like in gapped, stable regimes.

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

• Metric/curvature (approx.): plug |∂_i u_a^R⟩ into biorthogonal g_ij^(a) = Re ⟨∂_i u_a^R | ∂_j u_a^R⟩_(biorth), and Omega_ij^(a) = 2 Im(·). Peaks in g arise from small gaps |mu_a − mu_b| → 0. This provides analytic predictions for CGT features without brute-force stencils.

---

## 18. Nodewise Susceptibility Xi_n: Definitions & Options

The curvature-induced bias Gamma_n = beta sum_{i<j} Omega_ij epsilon^{ij} Xi_n needs a principled Xi_n. We propose three families:

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

We specify three physically motivated readouts; all can include geometric memory via loop flux Phi_gamma.

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

1. Build L(lambda) for a minimal graph and verify exceptional points coincide with ridges in tr(g).
2. Compute biorthogonal Omega^(a) along (rho, tau) loops; confirm R_gamma ∝ sum_a w_a Phi_gamma^(a).
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

## 22. Memory terms M_n(Phi_gamma): concrete operational forms

We make the memory in C-layer readouts explicit and measurable.

A) Uniform geometric charge: M_n = chi_n * Phi_gamma, with chi_n a fixed weight (e.g., amplitude share |Psi_n|^2 averaged over the loop or normalized centrality). Predicts global, orientation-sensitive bias.

B) Direction-locked memory: M_n = Phi_gamma * s_n * (t_loop dot grad_theta_n), where s_n in [0,1] is local coherence and t_loop the loop’s orientation in parameter space mapped to a preferred transport direction on the graph. Links memory to phase gradients that steer flow.

C) Current-coupled memory: define edge current J_nm = w_nm * sqrt(p_n p_m) * sin(theta_m - theta_n). Let M_n_raw = sum_m J_nm - J_mn (net outgoing). Then use M_n = Phi_gamma * Norm(M_n_raw). Ties memory to a directly computed graph observable.

Report which form is used in each experiment. A is baseline; C is most physical when phase currents are meaningful.

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

* Primary formulation is discrete steps on a graph with delays. A formal continuous-time limit exists when the step size is small compared to local delay timescales and couplings vary slowly. In that limit, effective differential equations for amplitude (Q) and phase (Theta) can be written; projective normalization induces nonlinearity even if the underlying map is linear.

27.2 Adiabatic small-loop regime

* For parameter loops with small area A in the parameter manifold M and slow traversal (compared to a local spectral gap of the step operator L), the pumped bias obeys:
  R_gamma = kappa_1 * Phi_gamma + O(A^2) and flips sign under loop reversal. This is the regime in which curvature serves as the leading-order predictor.

27.3 Non-adiabatic regime

* Breakdown indicators: large Fubini–Study distance per step, small eigenvalue gaps of L, or rapid parameter changes. In this regime one should rely on coarse-grained curvature (time-averaged plaquettes) and nonlinear diagnostics (Section 25).

27.4 Mixed-state regime

* Under dephasing/noise, geometry should be read via CPTP/Uhlmann constructions (Section 16.2). Claims about integer-like plateaus are not made in this regime; robustness is still meaningful but quantization is not guaranteed.

---

## 28. Quantization Conditions for Topological Plateaus

We clarify when “integer-like” behavior is expected and when it is not.

* Parameter manifold: a torus (two knobs with periodic identification) or an effective torus via boundary gluing.
* Spectral gap: a nonzero gap separating a band or invariant subspace of the step operator L from the rest of the spectrum along the loop family.
* Smooth gauge: biorthogonal eigenvectors of L admit a smooth gauge on the torus (no singular patches within the gapped region).
* Consequence: integrated biorthogonal curvature over the torus yields a plateau-like integer C as long as the gap remains open. If the gap closes (exceptional points, band touching), C can jump. With disorder that does not close the gap, C is stable; with strong disorder, only robustness (not integrality) should be asserted.

---

## 29. Correspondence Principles (reductions to known models)

These reductions anchor CWT in established dynamics under specific limits.

29.1 Kuramoto reduction (Theta-only)

* If amplitudes are uniform/slow and the Q-layer does not reshape transport on the timescale of Theta coupling, the phase update reduces to a Kuramoto-type model with coupling matrix J. Standard order-parameter analyses apply (synchronization transition, etc.).

29.2 Markov diffusion (Q-only)

* If phases are randomized or dephased so geometric terms vanish, the evolution reduces to a Markov chain with transition matrix K(lambda). Sensitivity is then captured by the metric component g arising from how K depends on lambda; curvature is negligible.

29.3 Adiabatic pumping (Thouless analog)

* For small, slow loops on a toroidal parameter domain with a gapped invariant subspace, the loop-induced bias in classical readouts scales with Phi_gamma (curvature flux) and reverses with orientation, directly paralleling adiabatic pumps.

29.4 Near-unitary map (Schroedinger-like)

* If transport is nearly lossless and the normalization step is replaced by a constant-norm evolution, the composite step approaches a unitary-like map. In that limit, CGT coincides with the standard quantum geometric tensor for the effective band states.

---

## 30. Reparameterization and Gauge Invariance

* State gauge: replacing Psi by e^{i phi(lambda)} Psi leaves the CGT, curvature flux, and pumped-bias predictions invariant; numerics use parallel-transport gauge for stability.
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

* Define “law-waves” as slow, possibly autonomous dynamics of the control parameters lambda over M, governed by the action in Section 6.1 plus weak coupling to observables (feedback). In this view, the system explores M through waves in lambda, and the CGT shapes both the effort to move (metric term) and the directional bias (curvature term). This formalizes earlier informal usage and binds it to the control action.

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

“Law-waves” is optional shorthand. The substantive concept is **control-field dynamics** governed by the action in Section 6.1. To avoid unnecessary jargon, papers may omit the term entirely and refer only to control-field dynamics on the parameter manifold. The equations and predictions are unchanged.

## 34. Responses to Critical Review: Theory Integrations

34.1 Normalization and CGT (projective map)

* We use the projective map L_hat(psi) = L(lambda) * psi / || L(lambda) * psi ||. The CGT uses projected derivatives (I − |Psi⟩⟨Psi|) * d_i |Psi>, removing any component parallel to |Psi|. Therefore, any scalar rescaling of L (including normalization effects) does not change the CGT.
* Proposition (sketch): Let |Phi> = L|Psi| / || L|Psi| || and s_i = d_i log || L|Psi| ||. Then d_i |Phi> differs from the normalized (d_i L)|Psi| by a term proportional to |Phi| * s_i. The projector kills this parallel term, so metric and curvature are invariant to normalization. Bounds: if || d_i L || is bounded and || L|Psi| || >= c > 0 in the region, then the difference between naive and projected derivatives is O( || d_i L || / c ), while the projected CGT is invariant to s_i by construction.

34.2 Convergence of discrete estimators

* Assumptions: (C1) Psi(lambda) is C2 on the patch; (C2) min-overlap between neighboring samples >= s_min > 0; (C3) rectangular stencils with step sizes delta_i -> 0.
* Result (sketch): The metric estimator using projected finite differences is first-order accurate: bias = O(max_i delta_i). The Wilson-plaquette curvature converges with bias O(max_i delta_i) and variance reduced by micro-plaquette averaging.

34.3 Pure vs mixed-state geometry: switching rule

* Use pure-state CGT when (i) average two-point overlap |⟨Psi(lambda)|Psi(lambda+delta)⟩| >= 0.9 along the path and (ii) phase-coherence order parameter s_bar >= 0.5. Otherwise adopt the CPTP/Uhlmann geometry. Report which regime is used.

34.4 Physical interpretation of Psi

* Psi is a coherence-weighted occupancy field: |Psi_n|^2 equals the Q-layer occupancy share; arg Psi_n is the local phase clock derived from delays and Theta-couplings. Metric g measures susceptibility of this field to knob changes; curvature Omega measures holonomy of its phase-amplitude structure under loops in lambda. Observable consequences appear through edge currents and readout biases (see 34.7).

34.5 Causality and parameter-geometry

* Locality: propagation on the graph remains strictly local; the geometry lives on control space lambda. Varying lambda is a slow control field (possibly spatially uniform or region-local), not a hidden nonlocal interaction between nodes. No superluminal signaling is introduced; causal order is still set by graph delays.

34.6 Control action (Section 6.1) motivation

* The action S[lambda] = ∫(1/2 g_ij lambda_dot^i lambda_dot^j + A_i lambda_dot^i − U) has: (i) a kinetic cost penalizing rapid moves where the system is sensitive (least-effort scheduling), (ii) a geometric work term capturing path bias (a control “Lorentz force”), and (iii) a potential term encoding objectives. Symmetry: reparameterization invariance on lambda, and gauge invariance under A_i -> A_i + d_i chi.

34.7 Why curvature biases amplitudes (mechanism)

* Phase kicks A_i * Delta lambda^i change phase differences across edges, which changes sinusoidal current terms J_nm ∝ sqrt(p_n p_m) * sin(theta_m − theta_n). Over a loop, the net holonomy shifts average currents in a direction set by loop orientation. The Q-layer update then inherits a transverse bias. Xi_n modulates local susceptibility (valves); the sign comes from Omega.

34.8 Choosing Xi_n by principle

* Principles: locality, positivity, invariance under graph isomorphisms, minimal extra structure. The static choice (degree * eigenvector-centrality, normalized) obeys these and is the default. Dynamic Xi is for feedback studies; learned Xi is for task optimization and must be ablated.

34.9 Effect-size constant in R_gamma ≈ kappa1 * Phi_gamma

* Linear-response: kappa1 = eta * sum_n (d log P_out / d M_n) * S_n, where S_n links the memory term to the loop (e.g., normalized current response per unit Phi). Both can be calibrated from small dithers in lambda without computing Omega. Report kappa1 with confidence intervals alongside Phi.

34.10 Independent definitions of transitions (non-CGT)

* Q-only: spectral gap 1 − |lambda2(P)| of the Markov kernel P(lambda) approaching 0 indicates loss of mixing. Theta-only: Kuramoto order parameter r crossing a threshold indicates synchronization. Coupled: largest Floquet multiplier of the projective map crossing 1. Compare these to ridges in tr(g) to avoid circularity.

34.11 Sufficiency example for quantization (constructive)

* Example QP-1: a two-level projective map with two periodic knobs, whose right-eigenvector gives a smooth map from a parameter torus to the Bloch sphere with winding number 1. Under a maintained spectral gap, the integrated biorthogonal curvature equals 2π times this winding. (A short appendix with explicit matrices can be added on request.)

34.12 Perturbation validity bounds

* Valid when || (d_i L) L^{†} || * loop diameter << spectral gap of L on the relevant invariant subspace, and when the FS distance per step is small (e.g., < 0.1 rad). Outside this, use the nonlinear diagnostics in Section 25.

34.13 Complexity scaling note

* Baseline cost O(N * T) (N nodes, T tiles). Refinement multiplies only a fraction f of tiles by <= 4^{r_max}. Publish (N, T, f, r_max, s_min, CI stop rules) so reviewers can assess computational feasibility.

## 35. Appendix QP-1: explicit two-level example with quantized curvature

We construct a minimal two-level projective map with a gapped spectrum and a right-eigenvector that winds once over a toroidal parameter domain.

Setup

* Parameters: lambda = (x, y) on a 2D torus with x,y in [0,1) and periodic identification.
* Step operator: choose a normal (diagonalizable with orthonormal eigenvectors) map with fixed, separated eigenvalues to keep a spectral gap: L = V diag(μ1, μ2) V^{-1}, with |μ1| = 1, |μ2| = 1/2 (gap is constant).
* Right-eigenvectors: define the normalized eigenvector for μ1 by the Bloch-sphere spinor
  u_R(x,y) = [ cos(β(y)/2), exp(i α(x)) sin(β(y)/2) ]^T,
  with α(x) = 2π x and β(y) = π y (so the map from the torus to the sphere covers once as x,y sweep [0,1)).
* Left-eigenvectors: since L is normal in this construction, take u_L = u_R (biorthogonal pairing reduces to the standard inner product). For non-normal L one can apply standard biorthogonal normalization; the winding result persists as long as the gap stays open and u_L, u_R remain smooth.

Curvature and integral

* The Berry connection for the band is A = i u_L^† d u_R. The curvature is Omega = dA.
* For the above parameterization, Omega = (1/2) sin β dα ∧ dβ.
* Integrating over the torus (x,y in [0,1)) gives ∫_{T^2} Omega = 2π (winding number = 1).
* Conclusion: the integrated (biorthogonal) curvature equals 2π while the spectral gap remains open; small non-normal perturbations that do not close the gap leave the integer unchanged.

## 36. Coupling strength from phase holonomy to Q-bias

Mechanism chain: geometric phase (A_i dλ^i) → phase-difference shifts on edges → current shifts J_nm ∝ sqrt(p_n p_m) sin(θ_m − θ_n) → transverse amplitude bias in the Q update.

Linear-response scaling (adiabatic small-loop regime)

* Let s_bar be the average local coherence (0..1). Let G_theta be a typical magnitude of phase gradients across edges. For a loop with flux Phi_gamma, the leading-order pumped-bias magnitude scales as
  |R_gamma| ≈ η * s_bar * G_theta * kappa_loc * |Phi_gamma|,
  where η is the C-layer sensitivity parameter and kappa_loc aggregates local susceptibilities (e.g., mean Xi_n on the active region). Orientation reversal flips the sign.
  Breakdown indicators
* s_bar → 0 (strong dephasing), G_theta ≈ 0 (flat phases), or large FS distance per step (> 0.1 rad) that invalidates linear response. Near-exceptional points, nonlinearity can dominate.

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
3. Run the loop twice (CW/CCW). Use the current-coupled memory readout. Measure R_gamma.
4. Verify sign reversal R_gamma(CW) = - R_gamma(CCW) and proportionality to Phi_gamma for small area.
5. Independently compute Kuramoto order parameter r and Markov spectral gap to locate the synchronization/mixing transition. Compare to ridges in tr(g).
   Expected outcomes

* Near the sync transition, tr(g) peaks and small loops produce measurable R_gamma with sign flip on reversal. Far from sync (dephased or fully locked), R_gamma shrinks.

## 39. Failure modes and caveats

* Numerical: small overlaps (instability), gauge singularities near EPs, CI caps hit frequently on rough landscapes.
* Physical: dynamic Xi feedback can destabilize unless contraction safeguards are used; C-layer saturation (T→0 or thresholds too low) can mask geometric effects.
* Regime: non-adiabatic driving (large FS jumps) invalidates linear scaling; heavy disorder that closes gaps breaks topological plateaus.
* Interpretive: using CGT to both define and detect “criticality” is circular; rely on independent criteria (Section 34.10).

## 40. Benchmarks against simpler predictors

Baselines

* Metric-only predictor: use tr(g) and sqrt(det g) to flag critical tiles.
* Spectral-gap predictor: use gap of P(lambda) or of the projective map to flag transitions.
  Curvature-aware predictor
* Use Phi_gamma to predict the sign and magnitude of pumped bias; combine with metric for ranked search (metric finds hotspots; curvature predicts directional effects).
  Evaluation
* Metrics: AUC for hotspot detection, R^2 and slope for R_gamma vs Phi_gamma, calibration error for kappa1, stability rate (% of tiles meeting CI tolerance without maxing refinement).
* Ablations: compare default Xi vs dynamic/learned, and memory variants A/B/C.

## 41. Geometric universality classes (GUC)

We organize systems into classes that share geometry-driven behavior.

Criteria

* Symmetry of transport and coupling: reversibility of K, symmetry of J, presence of frustration or chirality.
* Graph ensemble invariants: degree distribution shape, clustering, modularity, spectral gap scaling with size.
* CGT critical exponents: scaling of tr(g) and |Omega| near a gap closing; codimension of exceptional points.
* Topological sector: integer-like index C on toroidal parameter domains.

Class examples

* GUC-A: reversible kernels on expander-like graphs, weak Theta coupling; sharp metric ridges, small curvature away from biased loops.
* GUC-B: chiral or anisotropic transport, moderate coherence; robust nonzero curvature and pumpable bias on small loops.
* GUC-C: modular graphs with weak inter-module edges; multiple ridges and multi-step geometric memory with module-specific signs.

Predictions

* Within a class, normalized ridge shapes and pumped-bias scaling collapse after rescaling by local gaps and thermometer levels.

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
4. Guarantees: nonzero loop flux in a gapped sector implies a nonzero achievable bias at small loop areas; sign controlled by orientation.

## 43. Noise resilience

Noise models

* Phase noise: additive phase jitter per step with given variance.
* Amplitude noise: small random mass transfers between neighbors.
* Delay jitter: random modulation of delays that feeds Theta clocking.

Effects and rules of thumb

* Coherence factor s_bar multiplies the leading-order pumped bias; orientation reversal still flips the sign until s_bar falls below a threshold.
* Mixed-state (CPTP) geometry remains well defined and gives robust, if non-quantized, flux until dephasing erases loop memory.
* The thermometer remains an early-warning signal under moderate noise; refine meshes only where it persists.

## 44. Linking CGT to emergent phenomena

Mapping

* Synchronization transition: rapid rise in Kuramoto order r and a co-located ridge in tr(g); small loops develop measurable R_gamma that vanishes deep in either dephased or fully locked regimes.
* Pattern selection and fronts: persistent sign structure in Omega across tiles biases front motion and selects one of several symmetry-related patterns under cyclical drives.
* Rectified transport: nonzero Omega plus anisotropy creates directional flows under cyclic control even when instantaneous kernels are symmetric.

## 45. Modeling real systems as graphs

Guidelines

* Nodes represent local state holders (oscillators, buses, servers, cells). Edges carry flow with weights from coupling strength or capacity. Delays encode processing, transmission, or reaction lags.
* Q layer comes from occupancy, load, or probability of activity; Theta from phase-like clocks (swing phase, rotation, signal phase, reaction phase).
* Parameter manifold examples: density and delay scale; coupling gain; anisotropy; external field strength.
  Examples
* Power distribution feeders with load-dependent delays and phase angles; predict geometric rectification under seasonal control loops.
* Neural microcircuits with local oscillations; map geometric memory to bias in spike counts under slow neuromodulatory cycles.
* Traffic or logistics networks with congestion-induced delays; use CGT to design loops that relieve bottlenecks directionally.

## 46. Timescale separation criteria

* Graph timescale: characteristic propagation and phase-locking time from local delays and coupling.
* Control timescale: time to traverse a loop segment in parameter space.
* Adiabatic regime when the average Fubini Study step per update is below about 0.1 and the control speed divided by the smallest spectral gap is small; otherwise treat as non-adiabatic.

## 47. Orientation reversal: first-order argument

For small, slow loops, the readout change is linear in the loop integral of the connection. Reversing the loop changes the sign of the integral while leaving all local susceptibilities unchanged to first order. Therefore the pumped bias changes sign. Higher order corrections appear at larger loop areas or near gap closings.

## 48. Representation invariance of predictions

Two representations that yield the same nodewise amplitudes and all phase differences up to a global gauge produce identical geometric objects and the same pumped-bias predictions. This fixes the operational meaning of the geometry independent of internal parameterization choices.

## 49. Candidate application domains

* Power grids and microgrids; delays from frequency and dispatch constraints.
* Neuronal populations and oscillatory circuits; delays from synaptic and conduction latencies.
* Swarm and robotic coordination; phase-like headings, delays from communication and actuation.
* Queues and microservices; occupancy and backpressure set delays and phases.
* Chemical or ecological networks; reaction or migration delays.

## 50. Empirical roadmap beyond toy models

* Validate QP-1 and the 3 node ring. Then scale to a small real dataset in one domain above.
* Show advantage over metric-only and spectral-only baselines on hotspot prediction and directional bias calibration.
* Publish full auditing tuple (N, T, f, r_max, s_min, CI rules) and preregistered hypotheses.
