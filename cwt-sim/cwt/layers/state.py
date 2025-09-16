"""State helpers shared across the Q and Θ layer implementations."""

from __future__ import annotations

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


def normalize_prob(p: np.ndarray, eps: float = 0.0) -> np.ndarray:
    """Return a normalized, non-negative probability vector.

    Parameters
    ----------
    p:
        Input array representing a (possibly unnormalised) probability vector.
    eps:
        Optional non-negative pseudocount added to every entry before
        normalisation. This can be used to avoid exactly zero support while
        keeping the result a proper probability distribution.

    Returns
    -------
    numpy.ndarray
        A new array whose entries are non-negative and sum to one. If the input
        carries no mass (all zeros or negative values only), the result falls
        back to the uniform distribution over the available entries.
    """

    if eps < 0:
        raise ValueError("eps must be non-negative.")

    arr = np.asarray(p, dtype=float).copy()
    if arr.ndim != 1:
        arr = arr.reshape(-1)

    if arr.size == 0:
        return arr

    np.maximum(arr, 0.0, out=arr)

    if eps:
        arr += eps

    total = float(arr.sum())

    if not np.isfinite(total) or total <= 0.0:
        return np.full(arr.shape, 1.0 / arr.size, dtype=float)

    return arr / total


def wrap_angles(theta: np.ndarray) -> np.ndarray:
    """Wrap angles to the interval ``(-π, π]`` while preserving shape."""

    angles = np.asarray(theta, dtype=float)
    wrapped = (angles + np.pi) % (2.0 * np.pi) - np.pi
    # Map the -π endpoint to +π to make the interval open on the left.
    wrapped = np.where(wrapped <= -np.pi, wrapped + 2.0 * np.pi, wrapped)
    return wrapped
