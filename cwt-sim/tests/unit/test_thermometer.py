"""Unit tests for the geometric thermometer estimator."""

from __future__ import annotations

import numpy as np
import pytest

from cwt.geometry.fs_distance import fs_distance
from cwt.geometry.psi import build_psi
from cwt.geometry.thermometer import thermometer_directional


def test_thermometer_directional_matches_weighted_fs_distance() -> None:
    base_probs = np.array([0.7, 0.3], dtype=float)
    theta0 = np.zeros_like(base_probs)
    Psi0 = build_psi(base_probs, theta0)

    delta = 0.1
    Psi_x = build_psi(base_probs, theta0 + np.array([delta, -delta]))
    Psi_y = build_psi(base_probs, theta0 + np.array([0.0, delta]))

    neighbors = {"x": Psi_x, "y": Psi_y}
    deltas = {"x": delta, "y": delta}
    weights = {"x": 2.0, "y": 0.5}

    result = thermometer_directional(Psi0, neighbors, deltas, weights)

    expected = weights["x"] * (fs_distance(Psi0, Psi_x) ** 2) / (delta**2) + weights["y"] * (
        fs_distance(Psi0, Psi_y) ** 2
    ) / (delta**2)
    assert result == pytest.approx(expected)


def test_thermometer_directional_requires_deltas() -> None:
    Psi0 = np.ones(2, dtype=complex) / np.sqrt(2.0)
    with pytest.raises(KeyError):
        thermometer_directional(Psi0, {"x": Psi0}, {}, None)


def test_thermometer_directional_rejects_zero_displacement() -> None:
    Psi0 = np.array([1.0, 0.0], dtype=complex)
    with pytest.raises(ValueError):
        thermometer_directional(Psi0, {"x": Psi0}, {"x": 0.0})
