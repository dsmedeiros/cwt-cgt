"""Tests for the optional operator-view utilities and QP-1 example."""

from __future__ import annotations

import numpy as np
import pytest
from scripts.cgt.external.qp1_calibration import _derive_sign_map, qp1_calibration

import experiments.operator_patch.run as operator_patch
from cwt.cgt.geometry import (
    projective_metric_trace_and_curvature as cgt_projective_geometry,
)
from cwt.cgt.jacobian import response_metric_trace_and_curvature
from cwt.cgt.models import BranchState
from cwt.geometry.coherence import (
    projective_metric_trace_and_curvature as coherence_projective_geometry,
)
from cwt.geometry.curvature import curvature_tile
from cwt.operator.biorth_geom import biorth_connection, biorth_curvature
from cwt.operator.L_map import (
    qp1_builder,
    qp1_eigenvalues,
    qp1_state,
    qp1_state_derivatives,
    qp1_step_operator,
)


def _metric_component(u: np.ndarray, du_a: np.ndarray, du_b: np.ndarray) -> float:
    overlap_a = np.vdot(u, du_a)
    overlap_b = np.vdot(u, du_b)
    inner = np.vdot(du_a, du_b)
    return float(np.real(inner - overlap_a.conjugate() * overlap_b))


def test_qp1_step_operator_eigenpairs_match_construction() -> None:
    op = qp1_step_operator()
    lam = {"x": 0.37, "y": 0.42}

    matrix = op.L(lam)
    assert matrix.shape == (2, 2)

    eigenvalues, eigenvectors = op.eigenpairs(lam)

    assert eigenvalues.shape == (2,)
    assert eigenvectors.shape == (2, 2)

    expected_values = qp1_eigenvalues(lam)
    assert np.allclose(eigenvalues, expected_values)

    for idx in range(2):
        vec = eigenvectors[:, idx]
        assert np.isclose(np.linalg.norm(vec), 1.0)
        residual = matrix @ vec - eigenvalues[idx] * vec
        assert np.linalg.norm(residual) < 1e-10

    normal_commutator = matrix @ matrix.conj().T - matrix.conj().T @ matrix
    assert np.linalg.norm(normal_commutator) < 1e-10


def test_qp1_curvature_integrates_to_quantized_value() -> None:
    lam = {"x": 0.0, "y": 0.0}

    ys = np.linspace(0.0, 1.0, 2048, endpoint=False)
    dy = 1.0 / len(ys)
    dx = 1.0  # ``A_x`` is independent of ``x`` for the analytic construction.

    total_curvature = 0.0

    for y in ys:
        lam["y"] = float(y)
        state = qp1_state(lam)
        d_x, d_y = qp1_state_derivatives(lam)

        A_x = biorth_connection(state, d_x)
        A_y = biorth_connection(state, d_y)

        # ``A_y`` vanishes identically for the chosen gauge; ``A_x`` is real.
        assert np.isclose(A_y, 0.0, atol=1e-12)
        expected_Ax = 2.0 * np.pi * np.sin(0.5 * np.pi * y) ** 2
        assert np.isclose(A_x.real, expected_Ax)
        assert abs(A_x.imag) < 1e-12

        dA_i = 0.0  # ∂_x A_y
        dA_j = (np.pi**2) * np.sin(np.pi * y)  # ∂_y A_x
        omega_density = biorth_curvature(A_x, A_y, dA_i, dA_j)
        total_curvature += omega_density * dx * dy

    assert np.isclose(total_curvature, -2.0 * np.pi, atol=5e-3)


def test_qp1_is_periodic_in_azimuth_but_not_in_polar_coordinate() -> None:
    def projector(x: float, y: float) -> np.ndarray:
        state = qp1_state({"x": x, "y": y})
        return np.outer(state, state.conj())

    np.testing.assert_allclose(projector(0.0, 0.37), projector(1.0, 0.37), atol=1e-12)
    np.testing.assert_allclose(
        qp1_builder({"x": 0.0, "y": 0.37}),
        qp1_builder({"x": 1.0, "y": 0.37}),
        atol=1e-12,
    )

    # Each polar boundary collapses its azimuthal circle to one projector.
    np.testing.assert_allclose(projector(0.23, 0.0), projector(0.73, 0.0), atol=1e-12)
    np.testing.assert_allclose(projector(0.23, 1.0), projector(0.73, 1.0), atol=1e-12)

    # The two collapsed boundaries are distinct poles, not a periodic y seam.
    assert not np.allclose(projector(0.23, 0.0), projector(0.23, 1.0), atol=1e-12)
    assert not np.allclose(
        qp1_builder({"x": 0.23, "y": 0.0}),
        qp1_builder({"x": 0.23, "y": 1.0}),
        atol=1e-12,
    )


def test_qp1_calibration_derives_sign_map_and_handles_indeterminate_inputs() -> None:
    payload = qp1_calibration(samples=64)

    assert payload["calibration_kind"] == "sphere_chart"
    assert payload["x_periodic"] is True
    assert payload["y_periodic"] is False
    assert payload["sign_map_analytic_from_impl"] == 1.0
    assert _derive_sign_map(-2.0, -3.0) == 1.0
    assert _derive_sign_map(0.0, -3.0) is None
    assert _derive_sign_map(float("nan"), -3.0) is None


def test_qp1_wilson_sign_map_and_orientation_reversal() -> None:
    x = 0.17
    y = 0.31
    delta_x = 1.0e-3
    delta_y = 1.0e-3

    psi0 = qp1_state({"x": x, "y": y})
    psi_i = qp1_state({"x": x + delta_x, "y": y})
    psi_ij = qp1_state({"x": x + delta_x, "y": y + delta_y})
    psi_j = qp1_state({"x": x, "y": y + delta_y})

    omega_impl, stats = curvature_tile(psi0, psi_i, psi_ij, psi_j, delta_x, delta_y)
    omega_reversed, _ = curvature_tile(psi0, psi_j, psi_ij, psi_i, delta_y, delta_x)

    omega_analytic = -(np.pi**2) * np.sin(np.pi * y)

    assert stats["min_overlap"] > 0.99
    assert np.isclose(omega_impl, omega_analytic, rtol=2.0e-3)
    assert np.sign(omega_impl) == np.sign(omega_analytic)
    assert np.isclose(omega_reversed, -omega_impl, rtol=1.0e-8, atol=1.0e-8)


def test_connection_curvature_identity_matches_positive_two_imaginary_cgt() -> None:
    x = 0.17
    y = 0.31
    state = qp1_state({"x": x, "y": y})
    d_x, d_y = qp1_state_derivatives({"x": x, "y": y})
    c_xy = np.vdot(d_x, d_y) - np.vdot(d_x, state) * np.vdot(state, d_y)
    omega_from_cgt = 2.0 * float(np.imag(c_xy))

    a_x = biorth_connection(state, d_x)
    a_y = biorth_connection(state, d_y)
    omega_from_connection = biorth_curvature(
        a_x,
        a_y,
        dA_i=0.0,
        dA_j=(np.pi**2) * np.sin(np.pi * y),
    )

    assert omega_from_connection == pytest.approx(omega_from_cgt)


def test_qp1_derivative_and_wilson_curvature_paths_share_sign() -> None:
    x = 0.17
    y = 0.31
    step = 1.0e-4
    state = qp1_state({"x": x, "y": y})
    psi_x_plus = qp1_state({"x": x + step, "y": y})
    psi_x_minus = qp1_state({"x": x - step, "y": y})
    psi_y_plus = qp1_state({"x": x, "y": y + step})
    psi_y_minus = qp1_state({"x": x, "y": y - step})

    _, omega_cgt = cgt_projective_geometry(
        state,
        psi_x_plus,
        psi_x_minus,
        psi_y_plus,
        psi_y_minus,
        step,
        step,
    )
    _, omega_coherence = coherence_projective_geometry(
        state,
        psi_x_plus,
        psi_x_minus,
        psi_y_plus,
        psi_y_minus,
        step,
        step,
    )

    half_step = step / 2.0
    psi_00 = qp1_state({"x": x - half_step, "y": y - half_step})
    psi_10 = qp1_state({"x": x + half_step, "y": y - half_step})
    psi_11 = qp1_state({"x": x + half_step, "y": y + half_step})
    psi_01 = qp1_state({"x": x - half_step, "y": y + half_step})
    omega_wilson, _ = curvature_tile(psi_00, psi_10, psi_11, psi_01, step, step)

    p = np.square(np.abs(state))
    theta = np.angle(state)
    dp_dy = np.array(
        [
            -0.5 * np.pi * np.sin(np.pi * y),
            0.5 * np.pi * np.sin(np.pi * y),
        ]
    )
    dtheta_dx = np.array([0.0, 2.0 * np.pi])
    branch_state = BranchState(p=p, theta=theta, kernel=np.eye(2))
    du_vec = np.concatenate([np.zeros(2), dtheta_dx])
    dv_vec = np.concatenate([dp_dy, np.zeros(2)])
    _, omega_jacobian = response_metric_trace_and_curvature(
        branch_state,
        du_vec,
        dv_vec,
    )

    expected = -(np.pi**2) * np.sin(np.pi * y)
    assert omega_cgt == pytest.approx(expected, rel=1.0e-6)
    assert omega_coherence == pytest.approx(expected, rel=1.0e-6)
    assert omega_jacobian == pytest.approx(expected, rel=1.0e-6)
    assert omega_wilson == pytest.approx(expected, rel=1.0e-6)


def test_operator_patch_uses_left_vector_and_derivative_order_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The operator patch must match the QP-1 connection convention."""

    monkeypatch.setattr(
        operator_patch,
        "_psi_state",
        lambda substrate, lam, config: qp1_state(lam),
    )
    y = 0.4
    omega = operator_patch._operator_curvature(
        substrate=None,
        config=None,
        center={"x": 0.2, "y": y},
        axes=("x", "y"),
        delta_i=1.0e-4,
        delta_j=1.0e-4,
    )

    assert omega == pytest.approx(-(np.pi**2) * np.sin(np.pi * y), rel=1.0e-3)


def test_qp1_metric_and_gap_fixtures_have_constructed_shared_peak() -> None:
    """Record the authored coincidence without treating it as causal evidence."""
    op = qp1_step_operator()
    lam = {"x": 0.0, "y": 0.0}

    ys = np.linspace(0.0, 1.0, 400, endpoint=False)
    trace_g = []
    gaps = []

    for y in ys:
        lam["y"] = float(y)
        eigenvalues, _ = op.eigenpairs(lam)
        gaps.append(abs(eigenvalues[0] - eigenvalues[1]))

        state = qp1_state(lam)
        d_x, d_y = qp1_state_derivatives(lam)
        g_xx = _metric_component(state, d_x, d_x)
        g_yy = _metric_component(state, d_y, d_y)
        trace_g.append(g_xx + g_yy)

    trace_g = np.asarray(trace_g)
    gaps = np.asarray(gaps)

    max_trace_idx = int(np.argmax(trace_g))
    min_gap_idx = int(np.argmin(gaps))

    assert max_trace_idx == min_gap_idx

    y_peak = ys[max_trace_idx]
    assert np.isclose(y_peak, 0.5)
    assert np.isclose(trace_g[max_trace_idx], 1.25 * np.pi**2)
    assert np.isclose(gaps[min_gap_idx], 0.2)

    edge_idx = 0
    assert trace_g[edge_idx] < trace_g[max_trace_idx]
    assert gaps[edge_idx] > gaps[min_gap_idx]
