"""Kernel definitions for propagation across the graph substrate."""

from __future__ import annotations

from typing import Callable

import numpy as np
import scipy.sparse as sp

from .substrate import GraphSubstrate

Kernel = Callable[[float], float]


def phi_exp_delay(tau_nm: float, tau_scale: float, rho: float, kappa: float) -> float:
    """Return an exponentially decaying delay weight.

    Parameters
    ----------
    tau_nm:
        Edge delay :math:`\tau_{nm}` in the substrate.
    tau_scale:
        Characteristic time scale :math:`\tau` controlling the decay.
    rho:
        Dimensionless delay sensitivity. Larger values accentuate the
        suppression of long delays.
    kappa:
        Non-negative scaling factor applied to the response. The argument is
        accepted for API compatibility with future anisotropic extensions.

    Returns
    -------
    float
        Non-negative kernel weight for the specified delay.
    """

    if tau_scale <= 0:
        raise ValueError("tau_scale must be positive.")
    if rho < 0:
        raise ValueError("rho must be non-negative.")
    if kappa < 0:
        raise ValueError("kappa must be non-negative.")

    tau_nm = float(tau_nm)
    tau_scale = float(tau_scale)
    rho = float(rho)
    kappa = float(kappa)

    base = np.exp(-rho * tau_nm / tau_scale)
    return float(kappa * base)


def build_transport_kernel(
    S: GraphSubstrate,
    rho: float,
    tau_scale: float,
    kappa: float = 1.0,
    phi_fn: Callable[[float, float, float, float], float] = phi_exp_delay,
    anisotropy_axis: np.ndarray | None = None,
) -> sp.csr_matrix:
    """Construct the column-stochastic transport kernel :math:`K`.

    Parameters
    ----------
    S:
        Graph substrate containing edge weights ``W`` and delays ``Tau``.
    rho:
        Delay sensitivity forwarded to ``phi_fn``.
    tau_scale:
        Characteristic time scale forwarded to ``phi_fn``.
    kappa:
        Scalar anisotropy parameter forwarded to ``phi_fn``. The parameter is
        currently interpreted as a non-negative scaling factor.
    phi_fn:
        Callable producing a non-negative scalar for each edge delay.
    anisotropy_axis:
        Optional placeholder for future directional anisotropy support. Passing
        a non-``None`` value raises :class:`NotImplementedError` for the time
        being.

    Returns
    -------
    scipy.sparse.csr_matrix
        Column-stochastic transport kernel ``K`` with shape ``(N, N)``.
    """

    if anisotropy_axis is not None:
        raise NotImplementedError("Directional anisotropy is not implemented yet.")

    if tau_scale <= 0:
        raise ValueError("tau_scale must be positive.")
    if rho < 0:
        raise ValueError("rho must be non-negative.")
    if kappa < 0:
        raise ValueError("kappa must be non-negative.")

    if not isinstance(S, GraphSubstrate):
        raise TypeError("S must be an instance of GraphSubstrate.")

    N = S.N
    if N == 0:
        return sp.csr_matrix((0, 0), dtype=float)

    W = S.W.tocsr()
    Tau = S.Tau.tocsr()

    if W.shape != Tau.shape:
        raise ValueError("Weight and delay matrices must share the same shape.")
    if W.shape != (N, N):
        raise ValueError("Weight and delay matrices must be square with size N x N.")

    if not (np.array_equal(W.indptr, Tau.indptr) and np.array_equal(W.indices, Tau.indices)):
        raise ValueError("Weight and delay matrices must share the same sparsity structure.")

    if phi_fn is None:
        raise TypeError("phi_fn must be callable.")

    tau_values = Tau.data
    phi_values = np.array([phi_fn(float(tau), tau_scale, rho, kappa) for tau in tau_values], dtype=float)

    if phi_values.size and not np.all(np.isfinite(phi_values)):
        raise ValueError("phi_fn produced non-finite values.")

    if phi_values.size and np.min(phi_values) < 0:
        raise ValueError("phi_fn produced negative values.")

    Phi = Tau.copy()
    if phi_values.size:
        Phi.data = phi_values
    else:
        Phi.data = np.array([], dtype=float)

    A = W.multiply(Phi)
    A = A.tocsr()
    A.eliminate_zeros()

    column_sums = np.array(A.sum(axis=0)).ravel()
    positive_support = column_sums > 0

    if np.any(positive_support):
        inv_sums = np.zeros_like(column_sums)
        inv_sums[positive_support] = 1.0 / column_sums[positive_support]
        scaling = sp.diags(inv_sums, format="csr")
        K = A @ scaling
    else:
        K = sp.csr_matrix(A.shape, dtype=float)

    zero_support = ~positive_support
    if np.any(zero_support):
        diag_entries = zero_support.astype(float)
        K = K + sp.diags(diag_entries, format="csr")

    K.eliminate_zeros()
    return K.tocsr()
