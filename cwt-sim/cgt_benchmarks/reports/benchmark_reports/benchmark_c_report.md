# benchmark_c benchmark report

**Description:** Three-node ring first positive signed-loop benchmark.
**Expected behavior:** Nonzero curvature on a trusted patch and signed loop response.
**Observed verdict:** PASS — positive signed-loop benchmark

## Scan summary

- Regimes: R1:63, R4:18
- Metric trace max/mean: 0.867714 / 0.507645
- Curvature |F| max/mean: 0.321600 / 0.150919
- Branch atlas: Persistent branch counts = ambiguous:18, main:63. Ambiguous/switch tiles = 18.

## Loop summary

- Trusted pair count: 4
- Excluded pair count: 0
- Sign-flip fraction (R1): 1.000000
- Fit slope vs signed flux: -0.005240
- Fit R² vs signed flux: 0.999390
- Orientation-gap max: 0.000119

## Generated plots

![metric heatmap](../plots/benchmark_C_ring/metric_heatmap.png)

![curvature heatmap](../plots/benchmark_C_ring/curvature_heatmap.png)

![coherence heatmap](../plots/benchmark_C_ring/coherence_heatmap.png)

![overlap heatmap](../plots/benchmark_C_ring/overlap_heatmap.png)

![softness heatmap](../plots/benchmark_C_ring/softness_heatmap.png)

![regime map](../plots/benchmark_C_ring/regime_map.png)

![branch map](../plots/benchmark_C_ring/branch_map.png)

![response vs signed flux](../plots/benchmark_C_ring/response_vs_flux.png)

![response vs signed area](../plots/benchmark_C_ring/response_vs_area.png)

![orientation gap](../plots/benchmark_C_ring/orientation_gap.png)
