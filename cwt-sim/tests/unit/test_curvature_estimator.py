"""Tests for the curvature Wilson-plaquette estimator."""

from __future__ import annotations

import numpy as np

from cwt.geometry.curvature import curvature_tile


def _normalize(vec: np.ndarray) -> np.ndarray:
    vec = np.asarray(vec, dtype=np.complex128)
    norm = np.linalg.norm(vec)
    assert norm > 0
    return vec / norm


def test_curvature_vanishes_for_nearby_states():
    rng = np.random.default_rng(123)

    base = _normalize(rng.normal(size=8) + 1j * rng.normal(size=8))
    noise = 1e-3

    def jitter() -> np.ndarray:
        return _normalize(base + noise * (rng.normal(size=8) + 1j * rng.normal(size=8)))

    psi_i = jitter()
    psi_j = jitter()
    psi_ij = jitter()

    delta = 0.1
    omega, stats = curvature_tile(base, psi_i, psi_ij, psi_j, delta, delta)

    assert np.isfinite(omega)
    assert stats["min_overlap"] > 0.8
    assert abs(omega) < 1e-3


def test_curvature_flips_sign_under_orientation_swap():
    psi0 = np.array([1.0, 0.0], dtype=np.complex128)
    psi_i = np.array([1.0, 0.0], dtype=np.complex128)
    psi_ij = np.array([1.0, 1.0], dtype=np.complex128) / np.sqrt(2)
    psi_j = np.array([1.0, 1j], dtype=np.complex128) / np.sqrt(2)

    delta_i = 0.1
    delta_j = 0.2

    omega_forward, stats_forward = curvature_tile(psi0, psi_i, psi_ij, psi_j, delta_i, delta_j)
    omega_reverse, stats_reverse = curvature_tile(psi0, psi_j, psi_ij, psi_i, delta_j, delta_i)

    assert np.isfinite(omega_forward)
    assert np.isfinite(omega_reverse)
    assert stats_forward["min_overlap"] > 0.0
    assert stats_reverse["min_overlap"] > 0.0
    assert np.isclose(omega_reverse, -omega_forward, atol=1e-8, rtol=1e-8)
    assert set(stats_forward["overlaps"]) == {"0->i", "i->ij", "ij->j", "j->0"}
