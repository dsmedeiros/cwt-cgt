"""Phase update helpers for the Θ layer."""

from __future__ import annotations

import numpy as np
import scipy.sparse as sp

from ..graph.substrate import GraphSubstrate
from .state import wrap_angles


def omega_from_delays(
    S: GraphSubstrate,
    rho: float,
    tau_scale: float,
    omega_scale: float = 1.0,
) -> np.ndarray:
    """Derive nodewise intrinsic frequencies from outgoing edge delays."""

    if tau_scale <= 0:
        raise ValueError("tau_scale must be positive.")
    if rho < 0:
        raise ValueError("rho must be non-negative.")
    if omega_scale < 0:
        raise ValueError("omega_scale must be non-negative.")

    if not isinstance(S, GraphSubstrate):
        raise TypeError("S must be a GraphSubstrate instance.")

    N = S.N
    if N == 0:
        return np.zeros((0,), dtype=float)

    Tau = S.Tau.tocsc()
    if Tau.shape != (N, N):
        raise ValueError("Tau matrix must be square with shape (N, N).")

    column_sums = np.array(Tau.sum(axis=0)).ravel()
    counts = np.diff(Tau.indptr)

    local_mean = np.zeros(N, dtype=float)
    positive_mask = counts > 0
    if np.any(positive_mask):
        local_mean[positive_mask] = column_sums[positive_mask] / counts[positive_mask]
        global_mean = column_sums[positive_mask].sum() / counts[positive_mask].sum()
    else:
        global_mean = float(tau_scale)

    local_mean[~positive_mask] = global_mean

    denom = 1.0 + (local_mean / float(tau_scale))
    omega = np.full(N, float(omega_scale), dtype=float) / denom
    return omega


def build_J_from_W(S: GraphSubstrate, zeta: float, symmetric: bool = True) -> np.ndarray:
    """Construct the Θ-layer coupling matrix from substrate weights."""

    if not isinstance(S, GraphSubstrate):
        raise TypeError("S must be a GraphSubstrate instance.")

    if S.N == 0:
        return np.zeros((0, 0), dtype=float)

    W = S.W.tocsr()
    if W.shape != (S.N, S.N):
        raise ValueError("Weight matrix must be square with shape (N, N).")

    if symmetric:
        W = 0.5 * (W + W.T)

    row_sums = np.array(W.sum(axis=1)).ravel()
    inv_row = np.zeros_like(row_sums, dtype=float)
    mask = row_sums > 0
    inv_row[mask] = 1.0 / row_sums[mask]

    normalised = sp.diags(inv_row, format="csr") @ W
    J = normalised.toarray()

    if symmetric:
        J = 0.5 * (J + J.T)

    return float(zeta) * J


def theta_step(
    theta: np.ndarray,
    omega_n: np.ndarray,
    J: np.ndarray,
    phase_kick: np.ndarray | None = None,
    *,
    phi_edge: np.ndarray | None = None,
) -> np.ndarray:
    """Advance the Θ-layer phases with Kuramoto-like coupling."""

    theta_arr = np.asarray(theta, dtype=float)
    omega_arr = np.asarray(omega_n, dtype=float)

    if theta_arr.shape != omega_arr.shape:
        raise ValueError("theta and omega_n must share the same shape.")

    J_arr = np.asarray(J, dtype=float)
    N = theta_arr.size
    if J_arr.shape != (N, N):
        raise ValueError("J must be a square (N, N) matrix aligned with theta.")

    if phase_kick is not None:
        kick = np.asarray(phase_kick, dtype=float)
        if kick.shape != theta_arr.shape:
            raise ValueError("phase_kick must have the same shape as theta.")
    else:
        kick = 0.0

    theta_diff = theta_arr[np.newaxis, :] - theta_arr[:, np.newaxis]

    if phi_edge is not None:
        phi_arr = np.asarray(phi_edge, dtype=float)
        if phi_arr.shape != (N, N):
            raise ValueError("phi_edge must be a square (N, N) matrix aligned with theta.")
        theta_diff = theta_diff - phi_arr

    coupling = np.sum(J_arr * np.sin(theta_diff), axis=1)

    theta_next = theta_arr + omega_arr + coupling + kick
    return wrap_angles(theta_next)
