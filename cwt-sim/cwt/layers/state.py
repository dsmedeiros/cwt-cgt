"""State helpers shared across the Q and Θ layer implementations."""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np


@dataclass
class LayersState:
    """Container bundling the probability and phase fields for the layers."""

    pQ: np.ndarray
    theta: np.ndarray
    last_lambda: dict[str, float] | None = None


# ``LayerState`` is kept as an alias for backward compatibility with the
# placeholder API used in earlier iterations of the package.
LayerState = LayersState


def normalize_prob(
    p: np.ndarray,
    eps: float = 0.0,
    *,
    return_stats: bool = False,
    clamp_warn_tol: float = 1e-12,
) -> np.ndarray | tuple[np.ndarray, dict[str, float | int | bool]]:
    """Return a normalized, non-negative probability vector.

    Parameters
    ----------
    p:
        Input array representing a (possibly unnormalised) probability vector.
    eps:
        Optional non-negative pseudocount added to every entry before
        normalisation. This can be used to avoid exactly zero support while
        keeping the result a proper probability distribution.

    return_stats:
        When ``True``, return a tuple ``(normalized, stats)`` where ``stats``
        includes observability fields describing clamping/fallback behavior.
    clamp_warn_tol:
        Tolerance for warning emission based on the total negative mass that
        was clamped to zero.

    Returns
    -------
    numpy.ndarray or tuple[numpy.ndarray, dict]
        A new array whose entries are non-negative and sum to one. If the input
        carries no mass (all zeros or negative values only), the result falls
        back to the uniform distribution over the available entries.
    """

    if eps < 0:
        raise ValueError("eps must be non-negative.")

    if clamp_warn_tol < 0:
        raise ValueError("clamp_warn_tol must be non-negative.")

    arr = np.asarray(p, dtype=float).copy()
    if arr.ndim != 1:
        arr = arr.reshape(-1)

    if arr.size == 0:
        if return_stats:
            return arr, {
                "neg_clamped_count": 0,
                "neg_clamped_mass": 0.0,
                "uniform_fallback": False,
            }
        return arr

    negatives = arr < 0.0
    neg_clamped_count = int(np.count_nonzero(negatives))
    neg_clamped_mass = float(-arr[negatives].sum()) if neg_clamped_count else 0.0

    np.maximum(arr, 0.0, out=arr)

    if eps:
        arr += eps

    total = float(arr.sum())

    uniform_fallback = bool((not np.isfinite(total)) or total <= 0.0)

    if neg_clamped_mass > clamp_warn_tol:
        warnings.warn(
            (
                "normalize_prob clamped negative probability mass "
                f"{neg_clamped_mass:.3e} across {neg_clamped_count} entries."
            ),
            RuntimeWarning,
            stacklevel=2,
        )

    if uniform_fallback:
        warnings.warn(
            "normalize_prob applied uniform fallback due to non-positive total mass.",
            RuntimeWarning,
            stacklevel=2,
        )
        normalized = np.full(arr.shape, 1.0 / arr.size, dtype=float)
    else:
        normalized = arr / total

    if not return_stats:
        return normalized

    return normalized, {
        "neg_clamped_count": neg_clamped_count,
        "neg_clamped_mass": neg_clamped_mass,
        "uniform_fallback": uniform_fallback,
    }


def wrap_angles(theta: np.ndarray) -> np.ndarray:
    """Wrap angles to the interval ``(-π, π]`` while preserving shape."""

    angles = np.asarray(theta, dtype=float)
    wrapped = np.angle(np.exp(1j * angles))
    # Map the -π endpoint to +π to make the interval open on the left.
    wrapped = np.where(np.isclose(wrapped, -np.pi), np.pi, wrapped)
    return wrapped
