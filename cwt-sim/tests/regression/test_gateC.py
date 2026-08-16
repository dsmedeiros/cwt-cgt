import numpy as np

from experiments.gateC_topology_robust import run


def test_gateC_flux_conditioned_loop_noise_robustness_construction():
    """Gate C checks programmed loop/noise behavior, not Chern robustness."""

    results = run.run_experiment(
        phase_std_values=[0.0, 0.05, 0.1, 0.2, 0.35],
        amp_noise=0.02,
        delay_std=0.02,
        num_trials=3,
        loop_steps=60,
        grid_size=6,
    )

    coherence_threshold = results.coherence_threshold
    overlap_threshold = results.overlap_threshold

    for graph in results.graphs:
        mean_values: list[float] = []
        pure_state_mask: list[bool] = []
        for level in graph.noise_levels:
            mean_bias = float(np.mean(level.R_gamma_samples()))
            mean_values.append(mean_bias)
            pure_state_mask.append(level.pure_state_criteria_met)

            if not level.pure_state_criteria_met:
                assert level.s_bar_mean < coherence_threshold or level.overlap_mean < overlap_threshold

        # Check sign persistence while the configured pure-state criteria hold.
        in_scope_means = [val for val, ok in zip(mean_values, pure_state_mask) if ok]
        if in_scope_means:
            base_sign = np.sign(in_scope_means[0])
            assert base_sign != 0
            for value in in_scope_means[1:]:
                assert np.sign(value) == base_sign

            # Magnitude should not increase while the configured criteria hold.
            magnitudes = [abs(val) for val in in_scope_means]
            for prev, curr in zip(magnitudes, magnitudes[1:]):
                assert curr <= prev + 5e-4

        # Magnitude should continue trending down across the full sweep
        magnitudes_all = [abs(val) for val in mean_values]
        for prev, curr in zip(magnitudes_all, magnitudes_all[1:]):
            assert curr <= prev + 5e-4

    payload = results.to_dict()
    assert payload["evidence_tier"] == "internal_synthetic"
    assert payload["claim_scope"] == "loop_noise_robustness_construction"
    assert payload["not_a_topology_test"] is True
    assert payload["mixed_state_fallback_implemented"] is False
    point = payload["graphs"][0]["noise_points"][0]
    assert "pure_state_criteria_met" in point
    assert "quantized" not in point

    report = run._render_report(results)
    assert "protocol/noise robustness only, not topology or quantization" in report
    assert "No mixed-state fallback is implemented" in report
    assert "Quantization claim" not in report
