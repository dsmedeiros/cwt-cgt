# Baselines & Alignment Tests — CWT-CGT Validation Framework

## Overview

The baseline suite serves as both **instrument validation** and **geometric universality testing**. Each baseline model (Kuramoto, SIS, Ising, Percolation) represents a well-studied dynamical system with known transition behavior. By running these models through the CWT-CGT analysis pipeline, we can verify that the causal geometric tensor captures known phase transitions — establishing confidence that the curvature machinery reflects real structure rather than artifact.

---

## Objectives

1. **Validate the instrument:** Confirm that CWT-CGT curvature signals coincide with classical transition lines.
2. **Demonstrate geometric universality:** Show that the same geometric relationships (curvature, adiabatic scaling, FS behavior) emerge across physically distinct systems.
3. **Quantify scaling behavior:** Measure the adiabatic scaling exponent (( α ≈ 2 )) across all baselines to test universality.

---

## Architecture

Each baseline model is a self-contained Python module under `cwt-sim/baselines/<model>/run.py` with the following structure:

* **Grid runner:** sweeps parameter ranges (e.g., coupling vs noise) to compute observables.
* **Proxy curvature:** numerical derivative of observable magnitudes.
* **CWT curvature:** optional intrinsic curvature derived from CWT-CGT bridge.
* **Outputs:** metrics.csv, heatmap images, top-K hotspots, optional loop runs.

All baselines conform to a shared CLI schema and artifact structure, ensuring interoperability with the Electron GUI, artifact browser, and loop analysis tools.

---

## Axis Mapping

The axis mapping (e.g., K→τ, Δ→ζ for Kuramoto) is **conceptual**, not literal. It aligns model parameters with their **functional analogs** in CWT-CGT to allow shared analysis pipelines and visualizations.

Example YAML entry:

```yaml
kuramoto:
  K: tau
  Delta: zeta
```

This does not mean τ = K physically; it means that *K plays the same dynamical role* as τ does in CWT — both act as control parameters influencing coherence and coupling strength.

---

## Validation Tiers

The validation process operates on two distinct levels:

### 1. Internal Validation (`--map-to-cwt=true`)

* Runs the baseline model through the CWT-CGT machinery.
* Tests whether the geometric tensor is **system-agnostic**.
* Confirms that applying CWT analysis to different systems yields coherent curvature structure.

### 2. External Validation (Proxy Alignment)

* Uses **independent observables** (r, I, M, S) to compute numerical gradients (|∂O/∂param|).
* Compares these proxy curvature ridges with the intrinsic CWT |Ω| ridges.
* Agreement between them validates **emergent geometric concordance** independent of CGT math.

---

## Curvature Modes Appendix: Intrinsic vs Proxy

| Aspect | Intrinsic (CWT-CGT) | Proxy (Observable-derived) |
| --- | --- | --- |
| **Definition** | Derived from the Causal Geometric Tensor and FS metric | Finite difference or susceptibility of observable vs control parameter |
| **Input** | Internal wavefunction geometry or simulated causal state | Measured order parameter (r, I, M, S) |
| **Formula** | $\Omega_{CWT} = \operatorname{Im}\langle \partial_\tau \psi \mid \partial_\zeta \psi \rangle$ | $\Omega_{proxy} \approx |\partial O / \partial x|$ |
| **Dependency** | Requires access to transport kernel and delay coupling | Computed purely from simulation outputs |
| **Purpose** | Captures intrinsic curvature of causal manifold | Captures emergent response geometry |
| **Validation role** | Confirms correctness of CGT curvature computation | Confirms universality of geometric behavior |

**Key point:** these two curvature measures share no computational pathway. Their alignment is not tautological — it’s empirical evidence that geometry manifests consistently across both intrinsic and observable domains.

---

## Scaling Consistency (α ≈ 2)

In adiabatic systems, Fubini–Study distance grows quadratically with perturbation amplitude (Δ ∝ ε²). CGT predicts that α ≈ 2 for curvature response/flux scaling near small, adiabatic loops.

**Important:** α applies to loop response / geometric flux vs amplitude — i.e., |R| or |Φ| ∝ (amplitude)². The FS step itself scales approximately linearly with amplitude and is used as a guard (to ensure the regime where the quadratic expansion is valid), not as the dependent variable for α.

To validate this:

* Each baseline loop computes FS p95 and curvature vs amplitude.
* Fit α from the log–log slope of |response/flux| vs amplitude.
* Consistent α ∈ [1.95, 2.05] across systems is strong evidence of geometric universality.

**Cross-references (`theory.md`):**

* §7.2 Readout/Response Observables — small loops yield response Rγ linear in flux; flux couples to oriented area → quadratic in amplitude.
* Curvature–area coupling (section preceding §7) — curvature contracts with the oriented area element (ε^{ij}).
* §46 Timescale separation criteria — FS guard/overlap bounds for adiabaticity.
* §47 Orientation reversal: first-order argument — sign flip under CW↔CCW and linearity in Φ.
* §27 Foundational Regimes and Limits — where adiabatic assumptions break.

---

## Empirical Outputs

Each baseline produces:

* **metrics.csv** — core observables and curvature metrics.
* **ω_heatmap.png** — geometric intensity plot.
* **top_ω_tiles.json** — key hotspots for loop testing.
* **loop_reports/** — per-hotspot FS/Φ/R measurements (if enabled).

These artifacts can be visualized in the GUI’s Baselines panel, compared against phase runs, and used to verify the system’s curvature alignment.

---

## Interpreting Misalignments

Misalignment between CWT and proxy curvature ridges does not necessarily mean the theory has failed — but it does highlight where deeper analysis is needed.

### 1. **Parameterization drift**

If axes are poorly scaled (e.g., τ or ζ not normalized to physical equivalents), ridge positions may appear offset. Reparameterization or axis normalization can restore alignment.

### 2. **Non-adiabatic regimes**

When FS p95 exceeds guard thresholds, adiabatic assumptions break down. Geometry may distort or shift relative to the observable ridge. Tightening the FS guard or reducing loop extent can reestablish consistency.

### 3. **Finite-size or sampling artifacts**

Small grids or short simulations introduce noise in observables and derivatives. Increasing grid density or smoothing the metric field often realigns curvature features.

### 4. **True physical divergence**

In rare cases, the proxy and intrinsic curvature may genuinely diverge. This suggests the system’s emergent macroscopic order is not directly governed by the same local causal geometry — an important signal for refining CGT’s scope.

**Interpretive heuristic:**

* *Offset ridge* → scaling or normalization issue.
* *Diffuse ridge* → noise or non-adiabatic behavior.
* *Missing ridge* → genuine geometric deviation.

These outcomes help separate computational errors from genuine theoretical boundary cases.

---

## Interpretation

When proxy and CWT curvature ridges coincide:

* It indicates **shared geometric structure** between emergent observables and causal wave transport.
* It implies **geometry is fundamental**, not emergent from a specific physical mechanism.

When α ≈ 2 holds across systems:

* It suggests a **universal geometric scaling law** underlying complex dynamics — the signature of geometric universality.

---

## Summary

The baselines framework ensures that the CWT-CGT engine is both *valid* and *meaningful*. It demonstrates that curvature, as captured by CGT, is not a model artifact but a reflection of real structural invariants present in diverse systems.

> **In short:** Baselines prove the ruler; phases use it to measure reality.
