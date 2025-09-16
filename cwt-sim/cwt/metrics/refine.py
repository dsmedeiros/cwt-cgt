"""Refinement metrics scaffolding."""

from __future__ import annotations


def placeholder_refine_score() -> float:
    """Return a neutral refine score."""
    return 0.0


def geom_score(
    tr_g: float,
    det_g: float,
    omega: float,
    alpha: float = 1.0,
    beta: float = 0.2,
    gamma: float = 0.5,
) -> float:
    """Return a scalar score summarising geometric diagnostics."""

    from math import sqrt

    det_term = sqrt(max(det_g, 0.0))
    return float(alpha) * float(tr_g) + float(beta) * det_term + float(gamma) * abs(float(omega))


__all__ = ["geom_score", "placeholder_refine_score"]
