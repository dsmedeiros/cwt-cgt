"""Unit tests for geometric coupling helpers."""

from __future__ import annotations

import numpy as np
import pytest

from cwt.orchestrator.with_geom import (
    curvature_bias,
    nodewise_connection_a_i,
    phase_kick,
)


def test_nodewise_connection_recovers_relative_phase() -> None:
    rng = np.random.default_rng(42)
    base_phase = rng.uniform(-np.pi, np.pi, size=7)
    Psi0 = np.exp(1j * base_phase)

    delta = 0.05
    local_shifts = rng.uniform(-0.3, 0.25, size=Psi0.shape)
    global_shift = 1.3
    Psi_i = Psi0 * np.exp(1j * (global_shift + delta * local_shifts))

    a_i = nodewise_connection_a_i(Psi0, Psi_i, delta)

    assert a_i.shape == Psi0.shape
    offset = a_i - local_shifts
    assert np.allclose(offset, np.full_like(offset, offset[0]))


def test_nodewise_connection_zero_when_identical() -> None:
    phases = np.linspace(-0.5, 0.9, num=5)
    Psi = np.exp(1j * phases)
    delta = 0.1

    a_i = nodewise_connection_a_i(Psi, Psi.copy(), delta)

    assert np.allclose(a_i, np.zeros_like(Psi.real))


def test_nodewise_connection_uniform_shift_returns_constant() -> None:
    phases = np.linspace(-1.0, 1.0, num=4)
    Psi0 = np.exp(1j * phases)
    delta = 0.2
    shift = 0.7
    Psi_i = Psi0 * np.exp(1j * (shift + delta * 0.5))

    a_i = nodewise_connection_a_i(Psi0, Psi_i, delta)
    assert np.allclose(a_i, np.full_like(Psi0.real, a_i[0]))


def test_phase_kick_combines_knobs() -> None:
    theta = np.zeros(4)
    A_per_knob = {
        "rho": np.full(theta.shape, 0.5),
        "tau": np.array([-0.1, 0.2, -0.3, 0.4]),
    }
    delta_lambda = {"rho": 0.2, "tau": -0.4}

    kick = phase_kick(theta, A_per_knob, delta_lambda)
    expected = A_per_knob["rho"] * 0.2 + A_per_knob["tau"] * -0.4

    assert np.allclose(kick, expected)


def test_phase_kick_missing_knob_raises() -> None:
    theta = np.zeros(2)
    A_per_knob = {"rho": np.zeros_like(theta)}
    delta_lambda = {"tau": 1.0}

    with pytest.raises(KeyError):
        phase_kick(theta, A_per_knob, delta_lambda)


def test_curvature_bias_scales_with_susceptibility_sum() -> None:
    rng = np.random.default_rng(7)
    Xi = rng.random(5)
    Xi /= Xi.sum()

    Omega_ij = {("rho", "tau"): 0.75}
    delta_area = 0.6
    alpha = 1.4
    beta = -0.5

    bias = curvature_bias(Xi, Omega_ij, delta_area, alpha, beta)
    omega_sum = 0.75
    scalar = alpha * beta * omega_sum * delta_area

    assert bias.shape == Xi.shape
    assert np.allclose(bias, Xi * scalar)
    assert bias.sum() == pytest.approx(scalar)


def test_curvature_bias_orientation_flip_changes_sign() -> None:
    Xi = np.array([0.3, 0.7])
    Xi /= Xi.sum()

    Omega_ij = {("tau", "rho"): 1.2}
    bias = curvature_bias(Xi, Omega_ij, delta_area=0.5, alpha=2.0, beta=1.0)

    omega_sum = -1.2  # orientation flipped relative to canonical order
    scalar = 2.0 * 1.0 * omega_sum * 0.5

    assert np.allclose(bias, Xi * scalar)
    assert bias.sum() == pytest.approx(scalar)


def test_curvature_bias_total_matches_alpha_beta_omega_delta_area() -> None:
    Xi = np.array([0.25, 0.5, 0.25])
    Xi /= Xi.sum()

    Omega_ij = {
        ("rho", "tau"): 0.4,
        ("tau", "kappa"): -0.15,
        ("kappa", "rho"): 0.05,
    }
    delta_area = 0.35
    alpha = 1.3
    beta = 0.9

    bias = curvature_bias(Xi, Omega_ij, delta_area, alpha, beta)

    oriented_sum = 0.0
    for (i, j), value in Omega_ij.items():
        pair = tuple(sorted((i, j)))
        sign = 1.0 if (i, j) == pair else -1.0
        oriented_sum += sign * float(value)

    expected_total = alpha * beta * delta_area * oriented_sum
    assert bias.sum() == pytest.approx(expected_total)
