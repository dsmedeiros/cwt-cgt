"""Tests for the optional operator-view utilities and QP-1 example."""

from __future__ import annotations

import numpy as np

from cwt.operator.biorth_geom import biorth_connection, biorth_curvature
from cwt.operator.L_map import (
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
        expected_Ax = -2.0 * np.pi * np.sin(0.5 * np.pi * y) ** 2
        assert np.isclose(A_x.real, expected_Ax)
        assert abs(A_x.imag) < 1e-12

        dA_i = 0.0  # ∂_x A_y
        dA_j = -(np.pi**2) * np.sin(np.pi * y)  # ∂_y A_x
        omega_density = biorth_curvature(A_x, A_y, dA_i, dA_j)
        total_curvature += omega_density * dx * dy

    assert np.isclose(total_curvature, 2.0 * np.pi, atol=5e-3)


def test_trace_metric_spikes_where_gap_shrinks() -> None:
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
