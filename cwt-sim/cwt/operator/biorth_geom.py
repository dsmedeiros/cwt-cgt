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


def biorth_curvature(A_i, A_j, dA_i, dA_j) -> float:
    """Return the curvature ``Ω_{ij} = ∂_i A_j − ∂_j A_i`` for a single band."""

    Ai = complex(A_i)
    Aj = complex(A_j)
    dAi = complex(dA_i)
    dAj = complex(dA_j)

    for value in (Ai, Aj, dAi, dAj):
        if not np.isfinite(value.real) or not np.isfinite(value.imag):
            raise ValueError("Non-finite value encountered in curvature inputs.")

    curvature = dAi - dAj
    return float(np.real(curvature))


__all__ = ["biorth_connection", "biorth_curvature"]
