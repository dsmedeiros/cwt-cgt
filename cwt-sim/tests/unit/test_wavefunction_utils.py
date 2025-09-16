"""Unit tests for wavefunction helpers."""

from __future__ import annotations

import numpy as np
import pytest

from cwt.geometry.psi import build_psi, inner


def test_build_psi_normalises_and_combines_phase() -> None:
    pQ = np.array([0.2, 0.3, 0.5], dtype=float)
    theta = np.array([0.0, np.pi / 2.0, -np.pi / 4.0], dtype=float)

    psi = build_psi(pQ, theta)

    expected = np.sqrt(pQ) * np.exp(1j * theta)
    expected = expected / np.linalg.norm(expected)

    assert np.isclose(np.linalg.norm(psi), 1.0)
    np.testing.assert_allclose(psi, expected)


def test_build_psi_validates_inputs() -> None:
    with pytest.raises(ValueError):
        build_psi(np.array([0.5, 0.5]), np.array([0.0]))

    with pytest.raises(ValueError):
        build_psi(np.array([-0.1, 1.1]), np.zeros(2))

    with pytest.raises(ValueError):
        build_psi(np.zeros(3), np.zeros(3))


def test_inner_matches_numpy_vdot() -> None:
    rng = np.random.default_rng(123)
    z = rng.normal(size=4) + 1j * rng.normal(size=4)
    w = rng.normal(size=4) + 1j * rng.normal(size=4)

    assert inner(z, w) == pytest.approx(np.vdot(z, w))
