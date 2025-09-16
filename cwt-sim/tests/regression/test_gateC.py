import numpy as np

from experiments.gateC_topology_robust import run


def test_gateC_noise_robustness_and_decay():
    results = run.run_experiment(
        sigma_phase_values=[0.0, 0.05, 0.1, 0.2, 0.35],
        sigma_amp=0.02,
        sigma_tau=0.02,
        num_trials=3,
        loop_steps=60,
        grid_size=6,
    )

    coherence_threshold = results.coherence_threshold
    overlap_threshold = results.overlap_threshold

    for graph in results.graphs:
        mean_values: list[float] = []
        quantized_mask: list[bool] = []
        for level in graph.noise_levels:
            mean_bias = float(np.mean(level.R_gamma_samples()))
            mean_values.append(mean_bias)
            quantized_mask.append(level.quantized)

            if not level.quantized:
                assert level.s_bar_mean < coherence_threshold or level.overlap_mean < overlap_threshold

        # Check sign persistence while quantized
        quantized_means = [val for val, q in zip(mean_values, quantized_mask) if q]
        if quantized_means:
            base_sign = np.sign(quantized_means[0])
            assert base_sign != 0
            for value in quantized_means[1:]:
                assert np.sign(value) == base_sign

            # Magnitude should not increase as noise grows while quantized
            magnitudes = [abs(val) for val in quantized_means]
            for prev, curr in zip(magnitudes, magnitudes[1:]):
                assert curr <= prev + 5e-4

        # Magnitude should continue trending down across the full sweep
        magnitudes_all = [abs(val) for val in mean_values]
        for prev, curr in zip(magnitudes_all, magnitudes_all[1:]):
            assert curr <= prev + 5e-4
