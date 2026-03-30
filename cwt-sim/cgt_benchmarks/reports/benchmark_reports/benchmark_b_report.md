# benchmark_b benchmark report

**Description:** Three-node line sensitivity without robust pumping.
**Expected behavior:** Metric hotspots, weak or patchy curvature, no strong loop law.
**Observed verdict:** PASS — null benchmark remains null-like

## Scan summary

- Regimes: R1:63, R4:18
- Metric trace max/mean: 0.024869 / 0.019926
- Curvature |F| max/mean: 1.823828e-15 / 8.077902e-16
- Branch atlas: Persistent branch counts = ambiguous:18, main:63. Ambiguous/switch tiles = 18.

## Loop summary

- Trusted pair count: 4
- Excluded pair count: 0
- Sign-flip fraction (R1): 0.000000
- Fit slope vs signed flux: None
- Fit R² vs signed flux: None
- Orientation-gap max: 4.440892e-16

## Generated plots

![metric heatmap](../plots/benchmark_B_line/metric_heatmap.png)

![curvature heatmap](../plots/benchmark_B_line/curvature_heatmap.png)

![coherence heatmap](../plots/benchmark_B_line/coherence_heatmap.png)

![overlap heatmap](../plots/benchmark_B_line/overlap_heatmap.png)

![softness heatmap](../plots/benchmark_B_line/softness_heatmap.png)

![regime map](../plots/benchmark_B_line/regime_map.png)

![branch map](../plots/benchmark_B_line/branch_map.png)

![response vs signed flux](../plots/benchmark_B_line/response_vs_flux.png)

![response vs signed area](../plots/benchmark_B_line/response_vs_area.png)

![orientation gap](../plots/benchmark_B_line/orientation_gap.png)
