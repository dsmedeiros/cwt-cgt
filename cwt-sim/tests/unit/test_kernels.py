"""Tests for graph transport kernels."""
from __future__ import annotations

import numpy as np
import pytest
import scipy.sparse as sp

from cwt.graph.factories import line3, ring3
from cwt.graph.kernels import build_transport_kernel, phi_exp_delay


def test_phi_exp_delay_behaves_as_expected() -> None:
    """The exponential delay kernel decays with the delay length."""

    tau = 2.0
    tau_scale = 4.0
    rho = 1.5
    kappa = 0.75

    expected = kappa * np.exp(-rho * tau / tau_scale)
    assert phi_exp_delay(tau, tau_scale, rho, kappa) == pytest.approx(expected)

    with pytest.raises(ValueError):
        phi_exp_delay(tau, 0.0, rho, kappa)


def test_transport_kernel_line3_column_normalisation() -> None:
    """Columns of the kernel sum to one and split mass symmetrically."""

    S = line3(weight=1.0, delay=1.0, bidir=True)
    K = build_transport_kernel(S, rho=1.0, tau_scale=1.0)

    assert sp.isspmatrix_csr(K)
    assert np.all(K.data >= 0)

    column_sums = np.asarray(K.sum(axis=0)).ravel()
    np.testing.assert_allclose(column_sums, np.ones(S.N))

    middle_column = K[:, 1].toarray().ravel()
    np.testing.assert_allclose(middle_column, np.array([0.5, 0.0, 0.5]))


def test_transport_kernel_zero_support_self_loop() -> None:
    """Columns without outgoing support acquire a self-loop."""

    S = line3(weight=1.0, delay=1.0, bidir=False)
    K = build_transport_kernel(S, rho=1.0, tau_scale=1.0)

    # Column for node with no outgoing edges becomes a self-loop.
    tail_column = K[:, 2].toarray().ravel()
    np.testing.assert_allclose(tail_column, np.array([0.0, 0.0, 1.0]))

    # Supported columns remain stochastic.
    supported_mask = np.array([True, True, False])
    column_sums = np.asarray(K.sum(axis=0)).ravel()
    np.testing.assert_allclose(column_sums[supported_mask], np.ones(2))


def test_transport_kernel_ring3_deterministic_flow() -> None:
    """On a ring the kernel routes each column to the next node."""

    S = ring3(weight=1.0, delay=1.0)
    K = build_transport_kernel(S, rho=1.0, tau_scale=1.0)

    expected = sp.eye(S.N, format="csr")[:, [1, 2, 0]]
    np.testing.assert_allclose(K.toarray(), expected.toarray())
