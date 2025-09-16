"""Tests for the projected finite-difference metric estimator."""

from __future__ import annotations

import numpy as np

from cwt.geometry.metric import metric_tile


def _random_state(rng: np.random.Generator, size: int) -> np.ndarray:
    vec = rng.normal(size=size) + 1j * rng.normal(size=size)
    norm = np.linalg.norm(vec)
    if norm == 0:
        raise RuntimeError("Random draw produced the zero vector, cannot normalize.")
    return vec / norm


def test_metric_invariant_under_global_phase() -> None:
    """Rephasing all wavefunctions together leaves the metric unchanged."""

    rng = np.random.default_rng(1234)
    psi0 = _random_state(rng, 8)
    delta_i = 1.0e-2
    delta_j = 2.0e-2

    direction_i = rng.normal(size=8) + 1j * rng.normal(size=8)
    direction_j = rng.normal(size=8) + 1j * rng.normal(size=8)

    psi_i = psi0 + delta_i * direction_i
    psi_j = psi0 + delta_j * direction_j

    base_metric = metric_tile(psi0, psi_i, psi_j, delta_i, delta_j)

    global_phase = np.exp(1j * rng.uniform(-np.pi, np.pi))
    phased_metric = metric_tile(
        psi0 * global_phase,
        psi_i * global_phase,
        psi_j * global_phase,
        delta_i,
        delta_j,
    )

    np.testing.assert_allclose(phased_metric, base_metric, atol=1e-12)


def test_metric_symmetry_and_positive_diagonal() -> None:
    """Random samples should yield a symmetric metric with PSD diagonals."""

    rng = np.random.default_rng(4321)
    size = 6

    for _ in range(32):
        psi0 = _random_state(rng, size)

        delta_i = rng.uniform(5.0e-3, 5.0e-2)
        delta_j = rng.uniform(5.0e-3, 5.0e-2)

        direction_i = rng.normal(size=size) + 1j * rng.normal(size=size)
        direction_j = rng.normal(size=size) + 1j * rng.normal(size=size)

        psi_i = psi0 + delta_i * direction_i
        psi_j = psi0 + delta_j * direction_j

        gij = metric_tile(psi0, psi_i, psi_j, delta_i, delta_j)
        gji = metric_tile(psi0, psi_j, psi_i, delta_j, delta_i)

        assert abs(gij - gji) <= 1e-10

        gii = metric_tile(psi0, psi_i, psi_i, delta_i, delta_i)
        gjj = metric_tile(psi0, psi_j, psi_j, delta_j, delta_j)

        assert gii >= -1e-12
        assert gjj >= -1e-12


def test_parallel_transport_gauge_removes_neighbor_phase() -> None:
    """Independent phase rotations of neighbours should not affect the metric."""

    rng = np.random.default_rng(314159)
    psi0 = _random_state(rng, 5)

    delta_i = 1.5e-2
    delta_j = 2.5e-2

    direction_i = rng.normal(size=5) + 1j * rng.normal(size=5)
    direction_j = rng.normal(size=5) + 1j * rng.normal(size=5)

    psi_i = psi0 + delta_i * direction_i
    psi_j = psi0 + delta_j * direction_j

    base_metric = metric_tile(psi0, psi_i, psi_j, delta_i, delta_j, use_pt_gauge=True)

    phase_i = np.exp(1j * np.pi / 3)
    phase_j = np.exp(-1j * np.pi / 5)

    gauged_metric = metric_tile(
        psi0,
        psi_i * phase_i,
        psi_j * phase_j,
        delta_i,
        delta_j,
        use_pt_gauge=True,
    )

    np.testing.assert_allclose(gauged_metric, base_metric, atol=1e-12)

    ungauged_metric = metric_tile(
        psi0,
        psi_i * phase_i,
        psi_j * phase_j,
        delta_i,
        delta_j,
        use_pt_gauge=False,
    )

    assert not np.isclose(ungauged_metric, base_metric, atol=1e-12)
