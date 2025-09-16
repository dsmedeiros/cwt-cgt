r"""Fubini-Study distance estimators for CGT."""

from __future__ import annotations

import numpy as np

from .psi import inner


def fs_distance(Psi_a: np.ndarray, Psi_b: np.ndarray, clamp: bool = True) -> float:
    r"""Compute the Fubini-Study distance between two state vectors.

    Parameters
    ----------
    Psi_a, Psi_b:
        Complex state vectors. They need not be normalized; normalization is
        inferred internally.
    clamp:
        If ``True`` the argument of ``arccos`` is clamped into ``[0, 1]`` to
        mitigate floating point error. When ``False`` an out-of-bounds argument
        raises ``ValueError``.

    Returns
    -------
    float
        The Fubini-Study distance :math:`d_{FS}(\Psi_a, \Psi_b)` in ``[0, \pi/2]``.

    Raises
    ------
    ValueError
        If either input has zero norm, or if ``clamp`` is ``False`` and the
        overlap falls outside ``[0, 1]`` beyond numerical tolerance.
    """

    Psi_a_arr = np.asarray(Psi_a, dtype=np.complex128)
    Psi_b_arr = np.asarray(Psi_b, dtype=np.complex128)

    norm_a = np.linalg.norm(Psi_a_arr)
    norm_b = np.linalg.norm(Psi_b_arr)
    if norm_a == 0 or norm_b == 0:
        raise ValueError("State vectors must be non-zero to compute distance.")

    overlap = inner(Psi_a_arr, Psi_b_arr)
    cos_arg_raw = float(np.abs(overlap) / (norm_a * norm_b))

    if clamp:
        cos_arg = float(np.clip(cos_arg_raw, 0.0, 1.0))
    else:
        tol = 1e-12
        if cos_arg_raw < -tol or cos_arg_raw > 1.0 + tol:
            raise ValueError("Fubini-Study argument must lie in [0, 1] when clamp is False.")
        # Ensure tiny numerical excursions do not trigger domain errors.
        cos_arg = min(max(cos_arg_raw, 0.0), 1.0)

    return float(np.arccos(cos_arg))


__all__ = ["fs_distance"]
