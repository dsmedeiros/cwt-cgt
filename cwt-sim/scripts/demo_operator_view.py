#!/usr/bin/env python3
"""Demo script for the operator-view QP-1 example."""

from __future__ import annotations

import argparse
import math

import numpy as np

from cwt.operator.biorth_geom import biorth_connection, biorth_curvature
from cwt.operator.L_map import qp1_state, qp1_state_derivatives


def integrate_qp1(num_samples: int) -> float:
    """Return the integral of Ω over the QP-1 control rectangle."""

    lam = {"x": 0.0, "y": 0.0}
    ys = np.linspace(0.0, 1.0, num=num_samples, endpoint=False)
    dy = 1.0 / max(num_samples, 1)
    dx = 1.0  # A_x is independent of x in this construction.

    total = 0.0
    for y in ys:
        lam["y"] = float(y)
        state = qp1_state(lam)
        d_x, d_y = qp1_state_derivatives(lam)

        A_x = biorth_connection(state, d_x)
        A_y = biorth_connection(state, d_y)

        dA_i = 0.0  # ∂_x A_y
        dA_j = -(math.pi**2) * math.sin(math.pi * y)  # ∂_y A_x
        omega_density = biorth_curvature(A_x, A_y, dA_i, dA_j)
        total += float(omega_density) * dx * dy

    return total


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--samples",
        type=int,
        default=2048,
        help="Number of discretisation samples along the y-direction.",
    )
    args = parser.parse_args()

    total = integrate_qp1(max(int(args.samples), 1))
    target = 2.0 * math.pi
    deviation = total - target

    print(f"Integral of Ω over the QP-1 rectangle: {total:.6f} rad")
    print(f"Deviation from 2π: {deviation:.6e} rad")


if __name__ == "__main__":
    main()
