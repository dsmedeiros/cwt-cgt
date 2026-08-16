# Gate B — Internal-synthetic exploratory metric-ridge scan

**Evidence tier:** internal synthetic; no external dataset was ingested.

**Evaluation scope:** the labels below were created post hoc on the evaluated grid
from the 25th-percentile spectral-gap and 75th-percentile $|\nabla r|$ thresholds.
The confidence intervals resample grid cells as IID despite spatial dependence.
They are descriptive same-grid diagnostics, not held-out validation.

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

To exercise the current uniform scalar $\kappa$ axis as an implementation
diagnostic, run:

```
python -m experiments.gateB_ridge_finder.run \
  --axes tau kappa --grid-size 21 \
  --tau-range 0.8 1.5 --kappa-range 0.5 1.5 \
  --output-dir runs/atlas_tau_kappa
```

Every positive value of this uniform scalar cancels under column normalization;
$\kappa=0$ is a degenerate self-loop fallback. This sweep therefore does not test
directional anisotropy.

## Universal diagnostics

Health — min overlap: n/a, mean overlap: n/a, tiles ≥ s_min: n/a, FS step mean: n/a,
p95: n/a, Ω CI mean width: n/a

Geometry — |Ω| mean/median: n/a / n/a, tr(g) mean/min/max: n/a / n/a / n/a

Loop — Φ: n/a, area: n/a, extents: ρ∈[0.000, 0.500], τ∈[0.500, 0.800], steps: n/a

Markers — spectral gap(P): n/a, |∇r|: n/a
- **Exploratory same-grid detection** treats $\mathrm{tr}\,g$ as the score and defines
  positives via the union of low-gap and high-$\|\nabla r\|$ tiles, with automatic
  fallback to $\|\nabla r\|$ alone when the gap lacks dynamic range. ROC curves and
  IID-cell bootstrap intervals accompany every sweep. These post-hoc labels and
  intervals do not provide an independent test set.

Heatmaps for $\mathrm{tr}\,g$, $|\Omega|$, spectral gap, and $r$, as well as ROC
plots and compressed metric bundles, are written under
`artifacts/<graph>/`.

## Results

### ring3

- Peak $\mathrm{tr}\,g$ values and large $\|\nabla r\|$ occur in the same evaluated
  grid corridor (see `artifacts/ring3/heatmaps.png`). This is a post-hoc descriptive
  co-location, not an ex-ante transition prediction.
- ROC AUC for hotspot detection: **0.908** with 95% CI **[0.876, 0.942]** from
  256 IID-cell bootstrap replicates. The value is exploratory and is not an
  independently held-out acceptance result.
- Correlations: $\mathrm{corr}(\mathrm{tr}\,g,\|\nabla r\|)=0.86$,
  $\mathrm{corr}(\mathrm{tr}\,g,\text{gap})\approx0$ because the gap is flat.

### random_regular

- Metric ridges, curvature hotspots, and large $\|\nabla r\|$ values cluster along
  a diagonal band on the same evaluated grid
  (`artifacts/random_regular/heatmaps.png`).
- ROC AUC: **0.881** with 95% CI **[0.844, 0.913]**.
- Correlations: $\mathrm{corr}(\mathrm{tr}\,g,\|\nabla r\|)=0.69$ and
  $\mathrm{corr}(\mathrm{tr}\,g,\text{gap})\approx-0.003$ globally, which is
  effectively null at the reported precision. This summary does not establish a
  separate local association.

## Notes

- The spectral gap is numerically degenerate on the directed ring, so the detector
  falls back to the Kuramoto gradient there. This adaptive, same-grid fallback is
  exploratory and must not be read as held-out confirmation.
- All requested elements—metric trace, curvature magnitude, independent markers,
  correlations, ROC plots, and IID-cell bootstrap CIs—are implemented as an
  internal-synthetic diagnostic construction.
