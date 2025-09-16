"""Wavefunction-related utilities for CGT estimators."""

from __future__ import annotations

import numpy as np


def build_psi(pQ: np.ndarray, theta: np.ndarray) -> np.ndarray:
    """Return normalized complex vector Psi = sqrt(pQ) * exp(1j * theta).

    Parameters
    ----------
    pQ:
        Probability weights associated with each component of the wavefunction.
    theta:
        Phase angles (in radians) for each component.

    Returns
    -------
    numpy.ndarray
        Normalized complex-valued wavefunction.

    Raises
    ------
    ValueError
        If the probability weights are negative, have incompatible shapes with
        the phases, or the resulting vector has vanishing norm.
    """

    pQ_arr = np.asarray(pQ, dtype=np.float64)
    theta_arr = np.asarray(theta, dtype=np.float64)

    if pQ_arr.shape != theta_arr.shape:
        raise ValueError("Probability amplitudes and phases must share a shape.")
    if np.any(pQ_arr < 0):
        raise ValueError("Probabilities must be non-negative to build a wavefunction.")

    psi = np.sqrt(pQ_arr) * np.exp(1j * theta_arr)
    norm = np.linalg.norm(psi)
    if not np.isfinite(norm) or norm <= 0.0:
        raise ValueError("Wavefunction norm must be positive and finite.")

    return psi / norm


def inner(z: np.ndarray, w: np.ndarray) -> complex:
    r"""Return the complex inner product :math:`\langle z | w \rangle`.

    The first argument is conjugated, matching the physics bra-ket convention.
    """

    z_arr = np.asarray(z, dtype=np.complex128)
    w_arr = np.asarray(w, dtype=np.complex128)
    return np.vdot(z_arr, w_arr)


__all__ = ["build_psi", "inner"]
