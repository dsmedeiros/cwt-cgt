"""Context helpers and geometric coupling utilities."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Mapping

import numpy as np


@contextmanager
def with_geometry() -> Iterator[None]:
    """Yield control with a placeholder geometry context."""

    yield


def nodewise_connection_a_i(
    Psi0: np.ndarray,
    Psi_i: np.ndarray,
    delta_i: float,
    eps: float = 1e-12,
) -> np.ndarray:
    """Return the Pancharatnam connection between two nodewise states.

    The connection is obtained from the phase difference between ``Psi0`` and
    ``Psi_i`` after fixing their relative gauge with the Pancharatnam (PT)
    convention.  The result is divided by ``delta_i`` to yield the discrete
    connection ``a_i(n)`` at every node ``n``.
    """

    Psi0_arr = np.asarray(Psi0, dtype=np.complex128)
    Psi_i_arr = np.asarray(Psi_i, dtype=np.complex128)

    if Psi0_arr.shape != Psi_i_arr.shape:
        raise ValueError("Psi0 and Psi_i must share the same shape.")

    delta = float(delta_i)
    if not np.isfinite(delta) or delta == 0.0:
        raise ValueError("delta_i must be a finite, non-zero value.")

    if eps <= 0:
        raise ValueError("eps must be strictly positive.")

    inner = np.vdot(Psi0_arr.ravel(), Psi_i_arr.ravel())
    if abs(inner) <= eps:
        gauge = 1.0
    else:
        gauge = np.exp(-1j * np.angle(inner))

    Psi_i_gauged = Psi_i_arr * gauge
    product = Psi_i_gauged * np.conj(Psi0_arr)

    phase_rel = np.angle(product)

    magnitude_mask = (np.abs(Psi0_arr) <= eps) & (np.abs(Psi_i_gauged) <= eps)
    if magnitude_mask.any():
        phase_rel = np.where(magnitude_mask, 0.0, phase_rel)

    connection = phase_rel / delta
    return np.asarray(connection, dtype=float)


def phase_kick(
    theta: np.ndarray,
    A_per_knob: Mapping[str, np.ndarray],
    delta_lambda: Mapping[str, float],
) -> np.ndarray:
    """Return per-node phase kicks from the supplied geometric connection."""

    theta_arr = np.asarray(theta, dtype=float)
    kick = np.zeros_like(theta_arr, dtype=float)

    if not delta_lambda:
        return kick

    for knob, delta in delta_lambda.items():
        if knob not in A_per_knob:
            raise KeyError(f"Missing connection data for knob '{knob}'.")

        a_i = np.asarray(A_per_knob[knob], dtype=float)
        if a_i.shape != theta_arr.shape:
            raise ValueError("Each a_i must have the same shape as theta.")

        kick = kick + a_i * float(delta)

    return kick


def curvature_bias(
    Xi: np.ndarray,
    Omega_ij: Mapping[tuple[str, str], float],
    delta_area: float,
    alpha: float,
    beta: float,
) -> np.ndarray:
    """Compute the curvature-driven bias for the Q-layer update."""

    Xi_arr = np.asarray(Xi, dtype=float)
    if Xi_arr.ndim == 0:
        Xi_arr = Xi_arr.reshape(())

    oriented_sum_per_pair: dict[tuple[str, str], float] = {}
    for (i, j), value in Omega_ij.items():
        if i == j:
            continue
        pair = tuple(sorted((i, j)))
        sign = 1.0 if (i, j) == pair else -1.0
        oriented_sum_per_pair[pair] = oriented_sum_per_pair.get(pair, 0.0) + sign * float(value)

    oriented_sum = float(sum(oriented_sum_per_pair.values()))
    scalar = float(alpha) * float(beta) * float(delta_area) * oriented_sum

    return Xi_arr * scalar


def make_phi_edge_ring3(zeta_phase: float) -> np.ndarray:
    """Return frustrated edge phase offsets for the three-node ring."""

    phi = np.zeros((3, 3), dtype=float)
    phi[1, 0] = float(zeta_phase)
    phi[2, 1] = float(zeta_phase)
    phi[0, 2] = float(-2.0 * zeta_phase)
    return phi
