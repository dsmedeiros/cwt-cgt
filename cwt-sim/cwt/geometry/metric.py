"""Metric tensor tooling for CGT simulations."""

from __future__ import annotations

import numpy as np

from .gauge import parallel_transport_rephase
from .psi import inner


def _project_perpendicular(psi0: np.ndarray, delta: np.ndarray) -> np.ndarray:
    """Project ``delta`` onto the subspace orthogonal to ``psi0``."""

    return delta - psi0 * inner(psi0, delta)


def metric_tile(
    Psi0: np.ndarray,
    Psi_i: np.ndarray,
    Psi_j: np.ndarray,
    delta_i: float,
    delta_j: float,
    use_pt_gauge: bool = True,
) -> float:
    """Return the metric tensor element :math:`g_{ij}` for a 2D tile.

    Parameters
    ----------
    Psi0, Psi_i, Psi_j:
        Wavefunctions evaluated at the centre (``Psi0``) and at neighbouring
        lattice points along directions ``i`` and ``j`` respectively.
    delta_i, delta_j:
        Finite-difference displacements along the corresponding directions.
    use_pt_gauge:
        Whether to align the neighbouring states using the parallel transport
        gauge before constructing the finite differences. Enabled by default.
    """

    psi0 = np.asarray(Psi0, dtype=np.complex128)
    psi_i = np.asarray(Psi_i, dtype=np.complex128)
    psi_j = np.asarray(Psi_j, dtype=np.complex128)

    delta_i_val = float(delta_i)
    delta_j_val = float(delta_j)

    if not np.isfinite(delta_i_val) or delta_i_val == 0.0:
        raise ValueError("delta_i must be a finite, non-zero scalar.")
    if not np.isfinite(delta_j_val) or delta_j_val == 0.0:
        raise ValueError("delta_j must be a finite, non-zero scalar.")

    if use_pt_gauge:
        rephased = parallel_transport_rephase(psi0, {"i": psi_i, "j": psi_j})
        psi_i = rephased["i"]
        psi_j = rephased["j"]

    delta_i_vec = (psi_i - psi0) / delta_i_val
    delta_j_vec = (psi_j - psi0) / delta_j_val

    delta_i_perp = _project_perpendicular(psi0, delta_i_vec)
    delta_j_perp = _project_perpendicular(psi0, delta_j_vec)

    gij = np.real(inner(delta_i_perp, delta_j_perp))
    return float(gij)


__all__ = ["metric_tile"]
