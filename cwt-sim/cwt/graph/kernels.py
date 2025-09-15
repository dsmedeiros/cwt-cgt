"""Kernel definitions for propagation across the graph substrate."""

from __future__ import annotations

from typing import Callable

Kernel = Callable[[float], float]


def placeholder_kernel(time: float) -> float:
    """Return a trivial kernel response for the given time."""
    return time
