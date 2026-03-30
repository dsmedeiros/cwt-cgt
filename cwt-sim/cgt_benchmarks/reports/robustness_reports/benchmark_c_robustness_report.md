# benchmark_c robustness report

**Description:** Three-node ring first positive signed-loop benchmark.
**Suite verdict:** PASS

## Protocols

### baseline_square_default

- Description: Baseline square loops at the canonical default center set.
- Verdict: PASS — positive loop law persists under this protocol
- Trusted pairs: 4
- Sign-flip fraction (R1): 1.000000
- Slope / R² vs signed flux: -0.005395 / 0.999944
- Result file: `benchmark_c_loops_baseline_square.json`
- Pair regimes: R1:4

### heldout_circle_default

- Description: Held-out circular loops at the same center set and side ladder.
- Verdict: PASS — positive loop law persists under this protocol
- Trusted pairs: 4
- Sign-flip fraction (R1): 1.000000
- Slope / R² vs signed flux: -0.005282 / 0.999194
- Result file: `benchmark_c_loops_heldout_circle.json`
- Pair regimes: R1:4

### offcenter_square

- Description: Square loops shifted away from the canonical center to test spatial robustness.
- Verdict: PASS — positive loop law persists with center-dependent local susceptibility
- Trusted pairs: 8
- Sign-flip fraction (R1): 1.000000
- Slope / R² vs signed flux: -0.004586 / 0.786179
- Result file: `benchmark_c_loops_offcenter_square.json`
- Pair regimes: R1:8

### offcenter_circle

- Description: Held-out circular loops on the off-center set.
- Verdict: PASS — positive loop law persists with center-dependent local susceptibility
- Trusted pairs: 8
- Sign-flip fraction (R1): 1.000000
- Slope / R² vs signed flux: -0.004468 / 0.698892
- Result file: `benchmark_c_loops_offcenter_circle.json`
- Pair regimes: R1:8

## Generated plots

![robustness slope summary](../plots/benchmark_C_ring/robustness/robustness_slope_summary.png)

![robustness sign-flip summary](../plots/benchmark_C_ring/robustness/robustness_signflip_summary.png)
