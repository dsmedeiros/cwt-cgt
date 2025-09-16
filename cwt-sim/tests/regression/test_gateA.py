import numpy as np

from experiments.gateA_rho_tau_loop import run


def _mean_ci(values):
    arr = np.asarray(list(values), dtype=float)
    if arr.size == 0:
        return float("nan"), (float("nan"), float("nan"))
    mean = float(arr.mean())
    if arr.size == 1:
        return mean, (mean, mean)
    std = float(arr.std(ddof=1))
    margin = 1.96 * std / np.sqrt(arr.size)
    return mean, (mean - margin, mean + margin)


def test_gateA_linear_and_orientation():
    results = run.run_experiment(num_trials=4, grid_size=8, s_min=0.6)

    for graph in results.graphs:
        extent_map = {extent.extent_fraction: extent for extent in graph.extents}
        assert 0.02 in extent_map and 0.04 in extent_map

        extent_small = extent_map[0.02]
        extent_large = extent_map[0.04]

        slope_small = np.mean(extent_small.slope_samples())
        slope_large = np.mean(extent_large.slope_samples())

        assert slope_small != 0.0

        ratio = slope_large / slope_small
        assert abs(ratio - 1.0) <= 0.2

        for extent in (extent_small, extent_large):
            pass_fraction = extent.overlap_pass_fraction()
            assert pass_fraction >= 0.9

            orient_mean, orient_ci = _mean_ci(extent.orientation_sums())
            assert orient_ci[0] <= 0.0 <= orient_ci[1]

            ccw_mean = np.mean(extent.ccw_bias())
            cw_mean = np.mean(extent.cw_bias())
            assert np.sign(ccw_mean) == -np.sign(cw_mean)
