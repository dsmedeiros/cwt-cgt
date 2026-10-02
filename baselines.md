# Baselines & Alignment Tests — CWT-CGT Validation Framework

## Overview

The baseline suite provides **instrument checks** and **conditional transition diagnostics** for canonical models (Kuramoto, SIS, Ising, Percolation). A known transition supplies an external reference, but a CGT metric or curvature ridge there is a hypothesis to test under a declared state encoding. Consistent with `theory.md`, passive sensitivity diagnostics and active oriented loop response require separate validation.

---

## Objectives

1. **Validate estimators:** Check observable derivatives and separately computed projective-state geometry against known controls.
2. **Test passive diagnostics:** Compare metric/curvature features with independently defined transitions under a frozen encoding; null or displaced ridges are admissible.
3. **Test active response separately:** Measure orientation-odd response with a flux-independent readout before testing curvature alignment or small-loop scaling.

---

## Architecture

Each baseline model is a self-contained Python module under `cwt-sim/baselines/<model>/run.py` with the following structure:

* **Grid runner:** sweeps parameter ranges (e.g., coupling vs noise) to compute observables.
* **Observable proxy:** numerical derivatives of observables; these are not automatically Berry curvature.
* **CGT geometry:** requires an explicit normalized state map and a separate metric/curvature calculation.
* **Outputs:** metrics.csv, heatmap images, top-K hotspots, optional loop runs.

All baselines conform to a shared CLI schema and artifact structure, ensuring interoperability with the Electron GUI, artifact browser, and loop analysis tools.

---

## Axis Mapping

The axis mapping (e.g., K→τ, Δ→ζ for Kuramoto) is a naming convention for shared analysis and visualization. It does not establish a physical equivalence or supply a CWT state encoding.

Example YAML entry:

```yaml
kuramoto:
  K: tau
  Delta: zeta
```

For percolation, `--map-to-cwt=true` only remaps the reported parameter axes. It does not run CWT transport or calculate intrinsic CGT geometry.

---

## Validation Tiers

The validation process operates on two distinct levels:

### 1. Internal Validation

* Tests the declared estimator, state map, normalization, and sign convention.
* Distinguishes implementation checks from evidence for a physical diagnostic or response law.
* Requires inspecting each runner; the mapping flag alone is not evidence of CGT computation.

### 2. External Validation (Proxy Alignment)

* Defines transitions from model-specific criteria before inspecting CGT fields.
* Compares those criteria with separately computed CGT geometry using a frozen state encoding and held-out evaluation.
* Reports dependence between estimators: coincident derivatives of the same observable are not independent evidence for CGT.

---

## Curvature Modes Appendix: Intrinsic vs Proxy

| Aspect | Intrinsic (CWT-CGT) | Proxy (Observable-derived) |
| --- | --- | --- |
| **Definition** | Derived from the Causal Geometric Tensor and FS metric | Finite difference or susceptibility of observable vs control parameter |
| **Input** | Internal wavefunction geometry or simulated causal state | Measured order parameter (r, I, M, S) |
| **Formula** | $\mathcal C_{ij}=\langle\partial_i\psi|\Pi_\perp|\partial_j\psi\rangle$; curvature from its imaginary part under the declared convention | $|\partial O/\partial x|$ or a specified mixed finite difference |
| **Dependency** | Requires a declared normalized state map | Computed from simulation observables |
| **Purpose** | Measures projective-state sensitivity and oriented geometry | Locates observable sensitivity |
| **Validation role** | Estimator checks; conditional diagnostic hypotheses | Transition reference or exploratory proxy |

**Dependence matters:** independence must be established for the actual implementation. The percolation runner's `omega` is a derivative or mixed derivative of `S_mean`; it is not a state-overlap Wilson loop or intrinsic CGT curvature, including when a legacy mode is named `wilson`.

---

## Scaling Consistency (α ≈ 2)

For a smooth non-degenerate state map, squared Fubini–Study distance is locally quadratic in displacement. Flux through a shrinking loop can scale as amplitude squared when its leading curvature contraction is nonzero. An active response inherits that scaling only with a separate response reduction and nonzero alignment coefficient.

**Important:** α applies to loop response / geometric flux vs amplitude — i.e., |R| or |Φ| ∝ (amplitude)². The FS step itself scales approximately linearly with amplitude and is used as a guard (to ensure the regime where the quadratic expansion is valid), not as the dependent variable for α.

To validate this:

* For runners with a declared state map, compute FS p95 and flux across a loop-amplitude ladder.
* Fit separate slopes for absolute response and absolute flux against amplitude; do not fit their ratio as an area law.
* Report fit uncertainty, loop-shape dependence, and vanishing-leading-term controls; an exponent near two alone does not establish geometric universality.

**Cross-references (`theory.md`):**

* §7.2 Readout/Response Observables — response/flux alignment is conditional on a non-degenerate readout and controlled remainder.
* Curvature–area coupling (section preceding §7) — curvature contracts with the oriented area element (ε^{ij}).
* §46 Timescale separation criteria — FS guard/overlap bounds for adiabaticity.
* §47 Orientation reversal: first-order argument — if the small-loop response reduction holds, reversing the loop reverses the signed curvature integral and leading orientation-odd response term; alignment with CGT flux and control of the remainder remain separate requirements.
* §27 Foundational Regimes and Limits — where adiabatic assumptions break.

---

## Empirical Outputs

Each baseline produces:

* **metrics.csv** — core observables and curvature metrics.
* **ω_heatmap.png** — estimator heatmap; percolation uses an observable proxy.
* **top_ω_tiles.json** — key hotspots for loop testing.
* **loop_reports/** — per-hotspot FS/Φ/R measurements (if enabled).

These artifacts can be visualized in the GUI’s Baselines panel and compared against phase runs. Interpretation requires identifying which estimator produced each field.

---

## Interpreting Misalignments

Misalignment between a declared CGT diagnostic and an independent transition reference requires checking both numerical convergence and the diagnostic hypothesis. The result alone does not identify its cause.

### 1. **Parameterization drift**

Coordinate choices can alter component magnitudes and ridge locations. Freeze coordinates and scaling before evaluation; selecting a remapping to restore alignment after inspecting results is exploratory.

### 2. **Non-adiabatic regimes**

FS/overlap guards help identify estimator or loop-response validity problems. They do not guarantee a passive transition ridge or an active response-curvature relation.

### 3. **Finite-size or sampling artifacts**

Small grids or short simulations introduce noise in observables and derivatives. Test size and sampling convergence, and declare any smoothing before evaluating alignment.

### 4. **True physical divergence**

A transition can be visible in an observable or metric while Berry curvature remains zero. Missing or displaced curvature is an admissible result; quantify it before narrowing a model-specific diagnostic claim.

**Interpretive heuristic:**

* *Offset ridge* → investigate coordinates, convergence, and diagnostic mismatch.
* *Diffuse ridge* → investigate finite-size broadening and estimator uncertainty.
* *Missing ridge* → assess statistical power and retain the null diagnostic outcome.

These outcomes help separate computational errors from genuine theoretical boundary cases.

---

## Interpretation

When an independent transition reference and separately computed CGT feature coincide:

* It supports the specified passive diagnostic in that model, encoding, and regime, subject to held-out evaluation.
* It supplies no active loop-response law or universal geometric mechanism by itself.

When α ≈ 2 holds across systems:

* It is compatible with a smooth nonzero area term; response independence and alignment remain separate obligations.

---

## Summary

The baselines framework separates estimator correctness, passive transition diagnostics, and active response hypotheses. Current observable proxies alone do not establish CGT universality.

## Percolation definitions and theorem reference

The current baseline samples finite graphs with independently open bonds at probability `p`; positive `zeta` also removes nodes independently, creating mixed bond-site percolation. `S_mean` is the mean **largest-component fraction**, not mean cluster size. `giant_fraction` is the fraction of trials whose largest component meets the configured size threshold, not the infinite-cluster probability.

For the infinite nearest-neighbor square lattice with pure independent bonds (`zeta=0`), the exact critical probability is $p_c=1/2$. The approximately $0.5927$ square-lattice site threshold applies to a different model. Finite samples need not locate their strongest derivative at $1/2$, and node-damaged or non-square graph sweeps have no such exact threshold reference.

The result discussed in the Scientific American article is $\theta(p_c)=0$, where $\theta(p)=P_p(|C(0)|=\infty)$, for independent nearest-neighbor bond percolation on $\mathbb Z^d$, $d\ge2$. The newly resolved dimensions are 3–10; the 2D case was known. This establishes continuous onset with established results, but gives neither exact thresholds in those dimensions nor critical exponents or convergence rates. The [pinned primary release](https://github.com/anthropics/formal-math/tree/795efb86f191735c5481675763537cfb4ff37e55/percolation) reports machine verification with Lean and an independent kernel, while stating that independent human review had not occurred.

## Finite-size benchmark and scientific limits

The `experiments.percolation_finite_size.run` benchmark uses a fixed origin in pure bond boxes (`zeta=0`) and estimates the probability that it connects to the boundary of $B_L=[-L,L]^d$, at Chebyshev distance $L$, with nonperiodic boundaries. Start with 2D calibration at the exact $p_c=1/2$, then extend the same sampling protocol to 3D. The rounded 3D bond reference $p\approx0.2488$ is numerical, not exact; see [Wang et al., *Bond and site percolation in three dimensions* (2013)](https://doi.org/10.1103/PhysRevE.87.052107). The origin-to-boundary events on expanding boxes decrease to the infinite-cluster event, so the theorem provides a limiting target of zero at criticality; finite samples cannot prove that limit or determine its rate.

Freeze the probability-to-state encoding before comparing CGT sensitivity with these connectivity measurements. A normalized real square-root map, $\psi_a=\sqrt{q_a}$, provides a control: its metric can be nonzero while its Berry curvature vanishes wherever the encoding is smooth. Thus a transition-sensitive metric need not produce oriented curvature. This benchmark supplies no validation of active response, phase coherence, or Chern topology.

Run the frozen reference profile from the repository root after setting up `.venv`:

```bash
PYTHONPATH=cwt-sim .venv/bin/python -m experiments.percolation_finite_size.run \
  --run-name reference_20261001_v1 --dimensions 2,3 --radii 2,4,6 \
  --probabilities-2d 0.4,0.5,0.6 --probabilities-3d 0.2,0.2488,0.3 \
  --samples 512 --geometry-samples 512 --batches 3 --step 0.02 \
  --min-overlap 0.9 --seed 20261001
```

The report is written to `cwt-sim/experiments/percolation_finite_size/artifacts/reference_20261001_v1/REPORT.md`. Use a new `--run-name` for another run; existing run artifacts are preserved. This profile specifies a finite-size diagnostic and encoding control, not a theorem proof or independent CWT response validation.
