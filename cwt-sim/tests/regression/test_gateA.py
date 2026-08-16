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


def test_gateA_flux_conditioned_construction_consistency():
    """Gate A covers programmed flux-conditioned behavior, not independent evidence."""

    results = run.run_experiment(num_trials=4, grid_size=8, s_min=0.6)

    for graph in results.graphs:
        extent_map = {extent.extent_fraction: extent for extent in graph.extents}
        assert 0.02 in extent_map and 0.04 in extent_map

        extent_small = extent_map[0.02]
        extent_large = extent_map[0.04]

        response_per_flux_small = np.mean(extent_small.response_per_flux_samples())
        response_per_flux_large = np.mean(extent_large.response_per_flux_samples())

        assert response_per_flux_small != 0.0

        ratio = response_per_flux_large / response_per_flux_small
        assert abs(ratio - 1.0) <= 0.2

        for extent in (extent_small, extent_large):
            pass_fraction = extent.overlap_pass_fraction()
            assert pass_fraction >= 0.9

            orient_mean, orient_ci = _mean_ci(extent.orientation_sums())
            assert orient_ci[0] <= 0.0 <= orient_ci[1]

            ccw_mean = np.mean(extent.ccw_bias())
            cw_mean = np.mean(extent.cw_bias())
            assert np.sign(ccw_mean) == -np.sign(cw_mean)

    payload = results.to_dict()
    assert payload["evidence_tier"] == "internal_synthetic"
    assert payload["claim_scope"] == "flux_conditioned_construction_check"
    assert payload["external_dataset_ingested"] is False
    sample = payload["graphs"][0]["extents"][0]["samples"][0]["ccw"]
    assert "observed_response_per_flux" in sample
    assert "slope" not in sample

    report = run._render_report(results)
    assert "construction consistency only" in report
    assert "Observed R/Φ mean" in report
    assert "κ₁ mean" not in report
