"""Biorthogonal geometry helpers for operator-view experiments."""

from __future__ import annotations

import numpy as np


def _as_complex_vector(vec: np.ndarray) -> np.ndarray:
    arr = np.asarray(vec, dtype=complex)
    if arr.ndim == 1:
        return arr
    if arr.ndim == 2 and 1 in arr.shape:
        return arr.reshape(-1)
    raise ValueError("Vectors must be one-dimensional for biorthogonal products.")


def biorth_connection(uL: np.ndarray, duR: np.ndarray) -> complex:
    """Return the biorthogonal connection component ``i⟨u_L|∂u_R⟩``."""

    left = _as_complex_vector(uL)
    right_deriv = _as_complex_vector(duR)
    if left.shape != right_deriv.shape:
        raise ValueError("Left eigenvector and derivative must share the same dimensionality.")

    overlap = np.vdot(left, right_deriv)
    return 1j * overlap


def biorth_curvature(*, A_i, A_j, d_j_A_i, d_i_A_j) -> float:
    """Return the scalar biorthogonal curvature density for one band.

    Expected inputs are connection components and their crossed derivatives:

    * ``d_j_A_i = ∂_j A_i``
    * ``d_i_A_j = ∂_i A_j``
    * ``Ω_ij = d_i_A_j - d_j_A_i``

    ``A_i`` and ``A_j`` are retained for input validation so callers can catch
    non-finite connection values before downstream analysis.
    """

    Ai = complex(A_i)
    Aj = complex(A_j)
    d_j_Ai = complex(d_j_A_i)
    d_i_Aj = complex(d_i_A_j)

    for value in (Ai, Aj, d_j_Ai, d_i_Aj):
        if not np.isfinite(value.real) or not np.isfinite(value.imag):
            raise ValueError("Non-finite value encountered in curvature inputs.")

    curvature = d_i_Aj - d_j_Ai
    return float(np.real(curvature))


__all__ = ["biorth_connection", "biorth_curvature"]
