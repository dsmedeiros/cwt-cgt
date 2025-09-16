"""Gauge-handling utilities for CGT simulations."""

from __future__ import annotations

from typing import Mapping

import numpy as np

from .psi import inner


def parallel_transport_rephase(Psi0: np.ndarray, Psis: Mapping[str, np.ndarray]) -> dict[str, np.ndarray]:
    r"""Return phase-aligned neighbours under the parallel transport gauge.

    Parameters
    ----------
    Psi0:
        Reference wavefunction that defines the gauge. It is assumed to be
        normalized so that :math:`\langle\Psi_0 | \Psi_0\rangle = 1`.
    Psis:
        Mapping from direction labels to neighbouring wavefunctions.

    Returns
    -------
    dict[str, numpy.ndarray]
        A new dictionary with the same keys as ``Psis`` whose values have been
        multiplied by a phase factor chosen so that
        :math:`\langle\Psi_0|\Psi_k\rangle` is real and non-negative. If the
        overlap vanishes, the original vector is returned unchanged.
    """

    psi0 = np.asarray(Psi0, dtype=np.complex128)

    rephased: dict[str, np.ndarray] = {}
    for key, psi in Psis.items():
        psi_arr = np.asarray(psi, dtype=np.complex128)
        overlap = inner(psi0, psi_arr)
        magnitude = float(np.clip(np.abs(overlap), 0.0, 1.0))

        if magnitude <= 1e-15:
            phase = 1.0 + 0.0j
        else:
            phase = np.exp(-1j * np.angle(overlap))

        rephased[key] = psi_arr * phase

    return rephased


__all__ = ["parallel_transport_rephase"]
