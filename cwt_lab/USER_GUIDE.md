# CWT Lab – Operator Field Notes

The lab’s renderer mirrors the phase-oriented layout described in the root-level [User Guide](../USER_GUIDE.md), but the desktop workspace also carries extra tooling intended for analysts who want fast feedback without leaving the Electron shell. These notes focus on the Baselines panel introduced in the 0.7 series and document how to read the alignment cues it emits.

## Baselines & Alignment

The Baselines panel launches curated scans against classic statistical models so you can compare simulation output against well-studied transitions. Each run persists its CLI payload, stdout log, summary JSON, and derived artifacts such as `metrics.csv`, `top_omega_tiles.json`, and loop reports. Use the saved artifacts to calibrate physics-specific intuition before deploying bespoke experiments.

### Ising (2D lattice)

- **What the sweep does** – Walks temperature (T) versus external field (h) on a square lattice. Expect the heatmap ridge to sharpen near the critical band where \|M\| ≈ 0.5.
- **Observable outcomes** – The top-tile table should list neighbouring coordinates with consistent magnetisation signs and ω̂ spikes on either side of the ridge. Loop summaries labelled “Theory aligned” typically show FS < 0.2 with φ mirroring the analytic tanh transition.
- **Interpreting deviations** – If magnetisation signs alternate tile-by-tile or loop cards show frequent FS guard trips, broaden the h span or relax the loop delta scale before re-running.

### Kuramoto (synchronising oscillators)

- **What the sweep does** – Scans coupling strength κ versus frequency disorder σ on the graph specified in **Graph kind**/**Graph params**.
- **Observable outcomes** – Synchronisation shows up as bright ridges with order parameters r̄ and |ρ| trending toward 1 while the spectral gap narrows. Loop reports marked “Theory aligned” confirm the numeric ridge overlaps the analytic threshold.
- **Interpreting deviations** – If |ρ| stagnates below ≈0.4, extend the step budget to smooth out jitter or test denser graphs. Loop cards without the alignment badge usually indicate κ bounds that are too low.

### Bond percolation

- **What the sweep does** – Sweeps bond-occupation probability p and node damage ζ. The ζ = 0 slice matches undamaged bond percolation; ζ > 0 gives mixed bond-site percolation. The infinite undamaged square lattice has exact bond threshold pc = 0.5. Finite lattices round the transition, and damage changes the threshold.
- **Observable outcomes** – `S_mean` is the mean largest-component fraction, normalized by the original node count. It is not mean cluster size (susceptibility) and does not have the susceptibility's peak-and-collapse interpretation. `giant_fraction` is the frequency of trials whose largest component meets a chosen size cutoff, rather than giant-component density. Neither observable directly measures infinite-cluster probability.
- **Heatmaps and summaries** – Both heatmaps use derivatives of cluster observables: the primary map uses a p derivative or mixed finite difference of `S_mean`, while the combined proxy uses gradient magnitudes. Peaks indicate sensitivity; they do not independently validate intrinsic CGT curvature or state-overlap loop holonomy. Reports under `loops/` summarize hotspot proximity to a threshold reference; inspect the distance, tolerance, and reference assumptions in the JSON.
- **Interpreting deviations** – Compare lattice sizes and realization counts to assess finite-size rounding and sampling noise. At pc, the absence of an infinite cluster is compatible with large connected clusters on finite lattices; a cutoff-event frequency above 0.5 does not establish the infinite-volume transition.

### SIS (preview)

- **What the sweep does** – Captures infection (β) versus recovery (γ) layouts so you can stage comparisons before the simulator backend lands.
- **Observable outcomes** – Current builds echo the submitted configuration and persist seeds/steps; alignment metrics will arrive with the simulation engine.
- **Interpreting deviations** – Treat unexpected outputs as dry-run noise for now. The Help Drawer in the panel will announce when contagion metrics and trust flags are live.

### Reading the artifacts

- **Heatmap (`metrics.csv` + PNG)** – Hover over the heatmap to inspect exact parameter coordinates, ω̂ values, and observables. Peaks that align with known critical points confirm your scan bounds are reasonable.
- **Top tile table (`top_omega_tiles.json`)** – Lists the most energetic coordinates. Consistent ordering across repeated runs means your seed/step choices are stabilising.
- **Loop summaries (`loops/*.json`)** – For percolation these are hotspot proximity summaries, without FS or holonomy measurements. Other models may include FS guards and φ diagnostics; inspect the underlying report before interpreting a badge.

With these cues you can quickly sanity-check the simulator or a new environment configuration before committing to bespoke calibrations.
