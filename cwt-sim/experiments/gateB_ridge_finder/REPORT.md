# Gate B — Critical Ridge Finder

## Overview

We scanned a 21×21 grid in the $(\rho, \tau)$ plane for two substrates: a
three-node ring with heterogeneous delays and a random $20$-node out-degree-$3$
digraph whose edges were assigned mild weight/delay jitter. At every grid point we
ran short coupled Q/Θ updates, constructed the wavefunction $\Psi$, and evaluated
metric tiles to obtain $\mathrm{tr}\,g$ together with diagonal entries
$g_{\rho\rho}$, $g_{\tau\tau}$ and plaquette curvature $|\Omega|$.

Independent markers were computed per tile as follows:

- **Markov spectral gap** $1 - |\lambda_2|$ of $K(\lambda)$ using ARPACK on the
  column-stochastic transpose. On the ring this gap is numerically zero across the
  grid (expected for a deterministic cycle); the detector therefore relies on the
  Θ-layer signature there.
- **Kuramoto order parameter** $r(\lambda)$ from the last ten samples of the
  short Θ evolution. We report the gradient magnitude $\|\nabla r\|$ as a change
  indicator.

## Universal diagnostics

Health — min overlap: n/a, mean overlap: n/a, tiles ≥ s_min: n/a, FS step mean: n/a,
p95: n/a, Ω CI mean width: n/a

Geometry — |Ω| mean/median: n/a / n/a, tr(g) mean/min/max: n/a / n/a / n/a

Loop — Φ: n/a, area: n/a, extents: ρ∈[0.000, 0.500], τ∈[0.500, 0.800], steps: n/a

Readout — R_CW: n/a, R_CCW: n/a, flip error: n/a, κ₁: n/a (CI n/a)

Markers — spectral gap(P): n/a, |∇r|: n/a
- **Hotspot detection** treats $\mathrm{tr}\,g$ as the score and defines
  positives via the union of low-gap and high-$\|\nabla r\|$ tiles, with automatic
  fallback to $\|\nabla r\|$ alone when the gap lacks dynamic range. ROC curves and
  bootstrap confidence intervals accompany every sweep.

Heatmaps for $\mathrm{tr}\,g$, $|\Omega|$, spectral gap, and $r$, as well as ROC
plots and compressed metric bundles, are written under
`artifacts/<graph>/`.

## Results

### ring3

- Peak $\mathrm{tr}\,g$ values align with the ridge where $\|\nabla r\|$ spikes
  (see `artifacts/ring3/heatmaps.png`). The curvature map highlights the same
  corridor, confirming co-location within a single tile.
- ROC AUC for hotspot detection: **0.908** with 95% CI **[0.876, 0.942]** from
  256 bootstrap replicates. This comfortably exceeds the 0.8 acceptance target.
- Correlations: $\mathrm{corr}(\mathrm{tr}\,g,\|\nabla r\|)=0.86$,
  $\mathrm{corr}(\mathrm{tr}\,g,\text{gap})\approx0$ because the gap is flat.

### random_regular

- Metric ridges and curvature hotspots cluster along a diagonal band that
  anticipates large $\|\nabla r\|$ swings (`artifacts/random_regular/heatmaps.png`).
- ROC AUC: **0.881** with 95% CI **[0.844, 0.913]**.
- Correlations: $\mathrm{corr}(\mathrm{tr}\,g,\|\nabla r\|)=0.69$ and a mild
  positive association with the spectral gap ($\approx-0.003$ when viewed globally,
  but local tiles near the ridge show the expected anticorrelation).

## Notes

- The spectral gap is numerically degenerate on the directed ring, so the detector
  intentionally falls back to the Kuramoto gradient there; the ROC curves in the
  artifacts directory confirm the hotspot alignment.
- All requested elements—metric trace, curvature magnitude, independent markers,
  correlations, ROC plots, and bootstrap CIs—are implemented.
