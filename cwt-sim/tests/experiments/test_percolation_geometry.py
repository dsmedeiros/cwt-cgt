"""Frozen shell-state geometry and finite exact controls."""

import numpy as np
import pytest

from experiments.percolation_finite_size.geometry import (
    chain_control,
    chain_probabilities,
    controls,
    diamond_gluing,
    histogram_geometry,
    sample_geometry,
    sqrt_state,
)
from experiments.percolation_finite_size.model import (
    build_box,
    draw_uniforms,
    sample_shells,
    stable_seed,
)


def test_real_state_encoding_preserves_raw_probabilities_and_has_zero_phase():
    probabilities = chain_probabilities(0.4, 0.6)

    state = sqrt_state(probabilities * 100)

    assert probabilities == pytest.approx([0.6, 0.256, 0.144])
    assert state.real == pytest.approx(np.sqrt(probabilities))
    assert np.array_equal(state.imag, np.zeros(3))


def test_actual_estimators_converge_in_both_positive_metric_directions():
    coarse = chain_control(0.4, 0.6, 0.01)
    fine = chain_control(0.4, 0.6, 0.005)
    tiny = chain_control(0.4, 0.6, 0.00001)

    for name, exact in [("g_uu", 1 / (4 * 0.4 * 0.6)), ("g_vv", 0.4 / (1 - 0.6**2))]:
        assert fine[name] > 0
        assert abs(fine[name] - exact) < abs(coarse[name] - exact)
        assert tiny[name] == pytest.approx(exact, rel=1e-4)
    assert tiny["g_uv"] == pytest.approx(0, abs=1e-4)
    assert tiny["omega"] == 0
    assert tiny["trace_g"] == pytest.approx(1 / 0.96 + 0.625, rel=1e-4)


def test_zero_support_is_explicitly_excluded_without_smoothing():
    result = histogram_geometry(np.tile([1, 0, 2], (4, 1)), 0.01)

    assert result["excluded_reason"] == "zero_bin"
    assert result["histograms"] == [[1, 0, 2]] * 4
    assert result["support_sizes"] == [2] * 4
    assert result["trace_g"] is None and result["omega"] is None


def test_low_overlap_is_explicitly_excluded():
    result = histogram_geometry(np.array([[1, 9], [9, 1], [1, 9], [9, 1]]), 0.01, 0.9)

    assert result["excluded_reason"] == "low_overlap"
    assert result["min_overlap"] == pytest.approx(0.6)
    assert result["trace_g"] is None and result["omega"] is None


def test_sample_geometry_reuses_one_full_uniform_array_at_four_chart_corners():
    box = build_box(2, 1)
    uniforms = draw_uniforms(box, 100, stable_seed(17, 2, 1, 0.4, "geometry"))

    result = sample_geometry(box, 0.4, 0.5, 0.01, uniforms)

    expected = [
        sample_shells(box, u, v, uniforms).histogram.tolist()
        for u, v in [(0.4, 0.5), (0.41, 0.5), (0.41, 0.51), (0.4, 0.51)]
    ]
    assert result["histograms"] == expected
    assert result["trials"] == 100


@pytest.mark.parametrize("u,v,step", [(0, 0.5, 0.01), (0.5, 1, 0.01), (0.99, 0.5, 0.01)])
def test_chart_endpoints_are_excluded(u, v, step):
    result = sample_geometry(build_box(2, 1), u, v, step, np.zeros((1, 12)))

    assert result["excluded_reason"] == "chart_outside_open_domain"
    assert result["trace_g"] is None and result["omega"] is None


@pytest.mark.parametrize("weights", [[0, 0], [1, -1], [1, np.nan], [1, np.inf]])
def test_invalid_state_weights_fail(weights):
    with pytest.raises(ValueError):
        sqrt_state(np.asarray(weights))


@pytest.mark.parametrize("step", [0, -0.01, np.nan, np.inf])
def test_invalid_geometry_steps_fail(step):
    with pytest.raises(ValueError):
        histogram_geometry(np.ones((4, 3)), step)


@pytest.mark.parametrize("u,v", [(np.nan, 0.5), (0.5, np.inf)])
def test_nonfinite_chart_coordinates_fail(u, v):
    with pytest.raises(ValueError):
        sample_geometry(build_box(2, 1), u, v, 0.01, np.zeros((1, 12)))


@pytest.mark.parametrize("threshold", [np.nan, -0.1, 1.1])
def test_invalid_overlap_thresholds_fail(threshold):
    with pytest.raises(ValueError):
        histogram_geometry(np.ones((4, 3)), 0.01, threshold)


def test_excluded_chart_has_complete_result_schema_and_zero_actual_trials():
    box = build_box(2, 1)
    uniforms = draw_uniforms(box, 3, 17)

    excluded = sample_geometry(box, 0, 0.5, 0.01, uniforms)
    included = sample_geometry(box, 0.4, 0.5, 0.01, uniforms)

    assert excluded.keys() == included.keys()
    assert excluded["trials"] == 0
    assert all(excluded[name] is None for name in ["g_uu", "g_uv", "g_vv"])


@pytest.mark.parametrize("step", [1e-170, 1e200])
def test_unrepresentable_stencil_area_fails_before_geometry_estimators(step):
    with pytest.raises(ValueError, match="stencil area"):
        histogram_geometry(np.ones((4, 3)), step)


def test_heterogeneous_diamond_enumeration_matches_independent_connectivity_formulae():
    result = diamond_gluing(np.array([0.8, 0.6, 0.9, 0.7]))

    assert result["p_o_A"] == pytest.approx(0.92)
    assert result["p_o_b"] == pytest.approx(0.8376)
    assert result["p_a_b"] == pytest.approx([0.9336, 0.8296])
    assert result["t"] == pytest.approx(0.1704)
    assert result["bound"] == pytest.approx(0.7496)
    assert result["passed"] and result["configurations"] == 16
    assert controls()["chain"]["omega"] == 0
