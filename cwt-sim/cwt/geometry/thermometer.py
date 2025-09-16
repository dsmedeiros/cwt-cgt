"""Thermometer utilities for tracking effective temperatures."""

from __future__ import annotations

from typing import Mapping

import numpy as np

from .fs_distance import fs_distance


def thermometer_directional(
    Psi0: np.ndarray,
    Psi_neighbors: Mapping[str, np.ndarray],
    deltas: Mapping[str, float],
    weights: Mapping[str, float] | None = None,
) -> float:
    """Estimate the geometric thermometer from directional perturbations.

    Parameters
    ----------
    Psi0:
        Reference state vector.
    Psi_neighbors:
        Mapping from direction labels to neighbouring state vectors.
    deltas:
        Finite difference displacements corresponding to ``Psi_neighbors``.
    weights:
        Optional mapping of per-direction weights. Missing entries default to 1.

    Returns
    -------
    float
        The weighted sum :math:`\Theta_{geo} \approx \sum_i w_i d_{FS}(\Psi_0,\Psi_i)^2 / \delta_i^2`.

    Raises
    ------
    KeyError
        If a delta value is not provided for a given neighbour.
    ValueError
        If any supplied displacement is zero.
    """

    if not Psi_neighbors:
        return 0.0

    Psi0_arr = np.asarray(Psi0, dtype=np.complex128)

    total = 0.0
    for direction, Psi_i in Psi_neighbors.items():
        if direction not in deltas:
            raise KeyError(f"Missing delta for direction '{direction}'.")

        delta = float(deltas[direction])
        if delta == 0.0:
            raise ValueError("Directional displacements must be non-zero.")

        weight = 1.0
        if weights is not None:
            weight = float(weights.get(direction, 1.0))

        distance = fs_distance(Psi0_arr, np.asarray(Psi_i, dtype=np.complex128))
        total += weight * (distance ** 2) / (delta ** 2)

    return float(total)


__all__ = ["thermometer_directional"]
