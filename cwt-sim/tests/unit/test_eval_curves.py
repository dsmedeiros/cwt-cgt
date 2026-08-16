"""Unit tests for evaluation curve helpers."""

from __future__ import annotations

import numpy as np
import pytest

from cwt.metrics.eval_curves import (
    fs_adiabaticity_guard,
    metric_only_null_rejection,
    mixing_time_baseline,
    noise_threshold_report,
    non_degenerate_spectral_gap,
    orientation_antisymmetry_statistic,
    overlap_safe_tile_filter,
    scramble_response_summary,
    second_singular_value,
    summarize_loop,
)
from cwt.orchestrator.scheduler import RunRecord


def _blank_record(**kwargs) -> RunRecord:
    defaults = dict(
        meta={},
        lambda_path=[],
        delta_lambda=[],
        delta_area=[],
        pQ_traj=[np.zeros(0, dtype=float)],
        theta_traj=[np.zeros(0, dtype=float)],
        psi_traj=[np.zeros(0, dtype=complex)],
        fs_steps=[],
        overlaps_min=[],
        g_tiles=[],
        omega_tiles=[],
        phase_kicks=[],
        curvature_biases=[],
        clip_counts=[],
        readouts=[],
    )
    defaults.update(kwargs)
    return RunRecord(**defaults)


def test_summarize_loop_uses_omega_tiles_for_flux() -> None:
    record = _blank_record(
        delta_area=[10.0],
        omega_tiles=[
            {"omega": 0.5, "tile_area": 0.3},
            {"omega": -0.25, "tile_area": 0.2},
        ],
    )

    summary = summarize_loop(record)

    expected_flux = 0.5 * 0.3 + (-0.25) * 0.2
    assert summary.phi_flux == expected_flux


def test_summarize_loop_flux_defaults_to_zero_without_tiles() -> None:
    record = _blank_record(delta_area=[5.0], omega_tiles=[])

    summary = summarize_loop(record)

    assert summary.phi_flux == 0.0


def test_summarize_loop_bias_integrates_across_steps() -> None:
    record = _blank_record(
        curvature_biases=[
            np.array([0.1, -0.05]),
            np.array([0.0, 0.05]),
        ],
    )

    summary = summarize_loop(record)

    assert summary.R_bias == pytest.approx(0.1)


def test_summarize_loop_bias_uses_memory_weighting_when_available() -> None:
    record = _blank_record(
        curvature_biases=[
            np.array([0.2, 0.0]),
            np.array([0.1, 0.05]),
        ],
        readouts=[{"step": 1, "memory_form": "uniform_charge", "memory": [0.25, 0.75]}],
    )

    summary = summarize_loop(record)

    expected = np.dot(np.array([0.3, 0.05]), np.array([0.25, 0.75]))
    assert summary.R_bias == pytest.approx(expected)


def test_non_degenerate_spectral_gap_reports_top_degeneracy() -> None:
    degenerate = np.diag([1.0, 1.0, 0.5])
    nondegenerate = np.diag([1.0, 0.5, 0.2])

    assert non_degenerate_spectral_gap(degenerate) == 0.0
    assert non_degenerate_spectral_gap(nondegenerate) == pytest.approx(0.5)


def test_second_singular_value_and_mixing_time_baseline() -> None:
    matrix = np.diag([1.0, 0.5, 0.1])

    assert second_singular_value(matrix) == pytest.approx(0.5)
    assert mixing_time_baseline(matrix, eps=0.25) == pytest.approx(2.0)


def test_orientation_antisymmetry_statistic_scores_sign_reversal() -> None:
    stats = orientation_antisymmetry_statistic([0.4, 0.3], [-0.4, -0.3])

    assert stats["count"] == 2
    assert stats["score"] == pytest.approx(1.0)
    assert stats["symmetric_residual"] == pytest.approx(0.0)


def test_fs_guard_and_overlap_filter_mark_safe_tiles() -> None:
    adiabatic = fs_adiabaticity_guard([0.02, 0.04, 0.08], max_step=0.1)
    nonadiabatic = fs_adiabaticity_guard([0.02, 0.12], max_step=0.1)

    assert adiabatic["passed"] is True
    assert nonadiabatic["passed"] is False
    assert nonadiabatic["excluded_reason"] == "non_adiabatic_fs_step"
    np.testing.assert_array_equal(
        overlap_safe_tile_filter([0.95, 0.89, np.nan], threshold=0.9),
        np.array([True, False, False]),
    )


def test_metric_only_null_rejection_helper() -> None:
    report = metric_only_null_rejection(
        metric_scores=[1.0, 2.0, 3.0, 4.0],
        responses=[1.0, -1.0, 1.0, -1.0],
        max_abs_correlation=0.5,
    )

    assert report["reject_metric_only"] is True
    assert report["abs_correlation"] <= 0.5


def test_metric_only_null_rejection_requires_response_variation() -> None:
    report = metric_only_null_rejection(
        metric_scores=[1.0, 2.0, 3.0, 4.0],
        responses=[0.0, 0.0, 0.0, 0.0],
        max_abs_correlation=0.5,
    )

    assert report["reject_metric_only"] is False
    assert report["reason"] == "degenerate_responses"
    assert np.isnan(report["correlation"])


def test_loop_summary_labels_first_fs_step_without_calling_it_kappa1() -> None:
    angle = 0.3
    record = _blank_record(
        psi_traj=[
            np.array([1.0 + 0.0j, 0.0 + 0.0j]),
            np.array([np.cos(angle) + 0.0j, np.sin(angle) + 0.0j]),
        ],
        omega_tiles=[{"omega": 1.0, "tile_area": 0.5}],
        curvature_biases=[np.array([0.2, 0.0])],
    )

    summary = summarize_loop(record)

    assert summary.fs_stats["first_step"] == pytest.approx(angle)
    assert "kappa1" not in summary.fs_stats
    assert summary.R_bias / summary.phi_flux == pytest.approx(0.4)


def test_scramble_summary_detects_a_zero_and_a_signflip() -> None:
    report = scramble_response_summary(
        baseline_ccw=[0.4, 0.3],
        baseline_cw=[-0.4, -0.3],
        a_zero_ccw=[0.01, 0.0],
        a_zero_cw=[-0.01, 0.0],
        a_signflip_ccw=[-0.4, -0.3],
        a_signflip_cw=[0.4, 0.3],
    )

    assert report["a_zero_collapsed"] is True
    assert report["a_signflip_reversed"] is True


def test_noise_threshold_report_marks_illustrative_synthetic_phase_noise_flip() -> None:
    report = noise_threshold_report(
        s_bar_values=[0.99, 0.95, 0.90, 0.88, 0.84],
        responses=[1.00, 0.95, 0.70, -0.20, -0.45],
        mild_s_bar_floor=0.95,
    )

    assert report["reference_sign"] == 1
    assert report["sign_flip_s_bar"] == pytest.approx(0.88)
    assert report["mild_count"] == 2
    assert report["high_noise_excluded_count"] == 2
