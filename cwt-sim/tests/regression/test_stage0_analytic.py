"""Regression tests for the stage-0 analytic validation experiment."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

# Ensure the experiments package is importable.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.stage0_analytic.run import (  # noqa: E402
    run_dimer_experiment,
    run_line3_experiment,
    run_ring3_experiment,
)


def test_dimer_fs_distance_is_monotone_and_bounded() -> None:
    result = run_dimer_experiment()
    diffs = np.diff(result.fs_distance)
    assert np.all(diffs >= -1e-10)
    assert np.all(result.fs_distance <= (math.pi / 2.0) + 1e-10)
    assert np.allclose(result.fs_distance, result.fs_expected, atol=1e-10)
    assert np.max(np.abs(result.curvature_omegas)) < 1e-10


def test_line3_curvature_ci_contains_zero() -> None:
    result = run_line3_experiment()
    lower, upper = result.curvature_ci
    assert lower <= 0.0 <= upper
    assert result.ci_width() <= result.ci_tol + 1e-12
    assert np.all(np.isfinite(result.metric_values))


def test_ring3_orientation_flip() -> None:
    result = run_ring3_experiment()
    assert math.isfinite(result.omega_forward)
    assert math.isfinite(result.omega_reverse)
    assert result.orientation_flip_holds()
    assert abs(result.omega_forward) > 1e-4
