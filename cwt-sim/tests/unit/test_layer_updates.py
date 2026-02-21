"""Unit tests for Q and Θ layer update helpers."""

from __future__ import annotations

import math

import numpy as np
import pytest
import scipy.sparse as sp

from cwt.graph.substrate import GraphSubstrate, build_substrate
from cwt.layers.q_update import q_step
from cwt.layers.state import normalize_prob, wrap_angles
from cwt.layers.theta_update import build_J_from_W, omega_from_delays, theta_step

nx = pytest.importorskip("networkx")


def test_normalize_prob_uniform_fallback() -> None:
    vec = np.array([-1.0, -0.5, -3.0])
    with pytest.warns(RuntimeWarning) as caught:
        norm = normalize_prob(vec)

    assert any("uniform fallback" in str(item.message) for item in caught)
    assert norm.shape == vec.shape
    assert np.allclose(norm, np.full(vec.shape, 1.0 / vec.size))


def test_normalize_prob_returns_stats_and_warns_on_clamped_mass() -> None:
    vec = np.array([0.3, -0.2, 0.1])

    with pytest.warns(RuntimeWarning, match="clamped negative probability mass"):
        norm, stats = normalize_prob(vec, return_stats=True, clamp_warn_tol=1e-9)

    assert norm.sum() == pytest.approx(1.0)
    assert stats["neg_clamped_count"] == 1
    assert stats["neg_clamped_mass"] == pytest.approx(0.2)
    assert stats["uniform_fallback"] is False


def test_normalize_prob_warns_on_uniform_fallback_with_stats() -> None:
    vec = np.array([-1.0, -0.5, -3.0])

    with pytest.warns(RuntimeWarning) as caught:
        norm, stats = normalize_prob(vec, return_stats=True)

    assert any("uniform fallback" in str(item.message) for item in caught)

    assert np.allclose(norm, np.full(vec.shape, 1.0 / vec.size))
    assert stats["neg_clamped_count"] == 3
    assert stats["uniform_fallback"] is True


def test_wrap_angles_range_and_endpoint() -> None:
    angles = np.array([-3 * math.pi, -math.pi, -0.1, 0.0, math.pi, 3 * math.pi])
    wrapped = wrap_angles(angles)
    assert wrapped.shape == angles.shape
    assert np.all(wrapped > -math.pi)
    assert np.all(wrapped <= math.pi)
    assert wrapped[1] == pytest.approx(math.pi)
    assert wrapped[4] == pytest.approx(math.pi)


def test_q_step_identity_kernel_conserves_probability() -> None:
    rng = np.random.default_rng(123)
    p = normalize_prob(rng.random(6))
    K = sp.identity(p.size, format="csr")
    p_next, stats = q_step(p, K, eta=0.7)

    assert np.allclose(p_next, p)
    assert stats["clipped_count"] == 0
    assert stats["neg_before_clip"] == 0
    assert stats["norm_neg_clamped_count"] == 0
    assert stats["norm_neg_clamped_mass"] == pytest.approx(0.0)
    assert stats["norm_uniform_fallback"] is False


def test_q_step_clipping_and_normalisation() -> None:
    p = np.array([0.6, 0.3, 0.1])
    K = sp.identity(3, format="csr")
    bias = np.array([-1.2, 0.5, 0.0])

    p_next, stats = q_step(p, K, eta=1.0, geom_bias=bias, clip_floor=0.0)

    assert pytest.approx(1.0) == float(p_next.sum())
    assert np.all(p_next >= 0.0)
    assert stats["neg_before_clip"] > 0
    assert stats["clipped_count"] >= stats["neg_before_clip"]


def test_q_step_validate_kernel_accepts_stochastic_kernel() -> None:
    p = np.array([0.2, 0.5, 0.3])
    K = sp.csr_matrix(
        np.array(
            [
                [0.6, 0.0, 0.3],
                [0.4, 0.5, 0.2],
                [0.0, 0.5, 0.5],
            ]
        )
    )

    p_next, _ = q_step(p, K, eta=0.6, validate_kernel=True)
    assert p_next.sum() == pytest.approx(1.0)


def test_q_step_validate_kernel_rejects_non_stochastic_kernel() -> None:
    p = np.array([0.2, 0.5, 0.3])
    K = sp.csr_matrix(
        np.array(
            [
                [0.6, 0.0, 0.1],
                [0.4, 0.4, 0.2],
                [0.0, 0.4, 0.3],
            ]
        )
    )

    with pytest.raises(AssertionError, match="column-stochastic"):
        q_step(p, K, eta=0.6, validate_kernel=True)


def simple_substrate() -> GraphSubstrate:
    G = nx.DiGraph()
    G.add_edge(0, 1, weight=1.0, delay=1.0)
    G.add_edge(1, 0, weight=2.0, delay=3.0)
    G.add_node(2)
    return build_substrate(G)


def test_omega_from_delays_averages_outgoing_delays() -> None:
    S = simple_substrate()
    omega = omega_from_delays(S, rho=1.0, tau_scale=2.0, omega_scale=1.0)
    expected = np.array(
        [
            1.0 / (1.0 + 1.0 / 2.0),
            1.0 / (1.0 + 3.0 / 2.0),
            1.0 / (1.0 + 2.0 / 2.0),
        ]
    )
    assert omega == pytest.approx(expected)


def test_build_J_from_W_scaling_and_symmetry() -> None:
    S = simple_substrate()
    J_unit = build_J_from_W(S, zeta=1.0, symmetric=True)
    J_scaled = build_J_from_W(S, zeta=0.5, symmetric=True)

    assert J_unit.shape == (S.N, S.N)
    assert np.allclose(J_unit, J_unit.T)
    assert np.allclose(J_scaled, 0.5 * J_unit)


def test_theta_step_advances_by_intrinsic_frequency_when_decoupled() -> None:
    theta = np.array([-0.4, 1.2, 2.9])
    omega = np.array([0.1, -0.3, 0.5])
    J = np.zeros((3, 3))

    theta_next = theta_step(theta, omega, J)
    expected = wrap_angles(theta + omega)
    assert theta_next == pytest.approx(expected)


def test_theta_step_with_coupling_remains_finite() -> None:
    theta = np.array([0.0, 0.1])
    omega = np.zeros(2)
    J = np.array([[0.0, 0.05], [0.05, 0.0]])

    theta_next = theta_step(theta, omega, J)
    assert np.all(np.isfinite(theta_next))
    assert np.all(theta_next > -math.pi)
    assert np.all(theta_next <= math.pi)


def test_theta_step_respects_phi_edge_offsets() -> None:
    theta = np.array([0.2, -0.3])
    omega = np.zeros(2)
    J = np.array([[0.0, 0.5], [0.3, 0.0]])
    phi_edge = np.array([[0.0, 0.4], [-0.1, 0.0]])

    base = theta_step(theta, omega, J)
    frustrated = theta_step(theta, omega, J, phi_edge=phi_edge)

    theta_diff = theta[np.newaxis, :] - theta[:, np.newaxis] - phi_edge
    coupling_expected = np.sum(J * np.sin(theta_diff), axis=1)
    expected = wrap_angles(theta + coupling_expected)

    assert frustrated == pytest.approx(expected)
    assert not np.allclose(base, frustrated)
