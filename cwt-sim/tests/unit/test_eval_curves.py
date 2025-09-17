"""Unit tests for evaluation curve helpers."""

from __future__ import annotations

import numpy as np

from cwt.metrics.eval_curves import summarize_loop
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
