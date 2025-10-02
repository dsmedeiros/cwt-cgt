"""Tests for statistical helpers used in gateB ridge finder experiments."""

from __future__ import annotations

import math
from warnings import catch_warnings, simplefilter

import numpy as np

from experiments.gateB_ridge_finder.run import finite_correlation


def test_finite_correlation_returns_nan_with_insufficient_samples() -> None:
    a = np.array([1.0, np.nan, 3.0])
    b = np.array([1.0, 2.0, np.nan])
    result = finite_correlation(a, b)
    assert math.isnan(result)


def test_finite_correlation_returns_nan_when_variance_is_zero() -> None:
    a = np.array([2.0, 2.0, 2.0, 2.0])
    b = np.array([1.0, 2.0, 3.0, 4.0])
    with catch_warnings():
        simplefilter("error")
        result = finite_correlation(a, b)
    assert math.isnan(result)


def test_finite_correlation_matches_numpy_result_for_valid_inputs() -> None:
    rng = np.random.default_rng(42)
    a = rng.standard_normal(128)
    b = 0.3 * a + rng.standard_normal(128)
    expected = float(np.corrcoef(a, b)[0, 1])
    result = finite_correlation(a, b)
    assert math.isclose(result, expected, rel_tol=1e-12, abs_tol=1e-12)
