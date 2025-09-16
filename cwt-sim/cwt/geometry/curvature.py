r"""Curvature estimators for CGT simulations."""

from __future__ import annotations

from typing import Sequence

import numpy as np

from .psi import inner

_PT_EPS = 1e-15


def _as_complex_array(vec: np.ndarray) -> np.ndarray:
    """Return a complex128 copy of ``vec`` suitable for inner products."""

    arr = np.array(vec, dtype=np.complex128, copy=True)
    if arr.ndim == 0:
        raise ValueError("Wavefunctions must be array-like with at least one dimension.")
    return arr


def _validate_shapes(states: Sequence[np.ndarray]) -> None:
    """Ensure all states share the same shape."""

    reference_shape = states[0].shape
    for idx, psi in enumerate(states[1:], start=1):
        if psi.shape != reference_shape:
            raise ValueError(
                "All wavefunctions must share a common shape; "
                f"state 0 has shape {reference_shape}, state {idx} has shape {psi.shape}."
            )


def _parallel_transport_chain(states: Sequence[np.ndarray]) -> list[np.ndarray]:
    """Rephase each state relative to its predecessor using PT gauge."""

    aligned: list[np.ndarray] = [states[0]]
    for idx in range(1, len(states)):
        prev = aligned[idx - 1]
        current = states[idx]
        overlap = inner(prev, current)
        magnitude = np.abs(overlap)
        if magnitude > _PT_EPS:
            phase = np.exp(-1j * np.angle(overlap))
            current = current * phase
        aligned.append(current)
    return aligned


def _compute_loop_overlaps(states: Sequence[np.ndarray]):
    """Yield labels and overlaps along the Wilson plaquette loop."""

    labels = ("0->i", "i->ij", "ij->j", "j->0")
    pairs = (
        (states[0], states[1]),
        (states[1], states[2]),
        (states[2], states[3]),
        (states[3], states[0]),
    )
    for label, (left, right) in zip(labels, pairs):
        yield label, inner(left, right)


def curvature_tile(
    Psi0: np.ndarray,
    Psi_i: np.ndarray,
    Psi_ij: np.ndarray,
    Psi_j: np.ndarray,
    delta_i: float,
    delta_j: float,
    use_pt_gauge: bool = True,
) -> tuple[float, dict]:
    r"""Return the curvature :math:`\Omega_{ij}` estimated via a Wilson plaquette.

    Parameters
    ----------
    Psi0, Psi_i, Psi_ij, Psi_j:
        Wavefunctions evaluated on the four corners of a tile in parameter space,
        ordered such that ``Psi_i`` lies along the ``+i`` direction from ``Psi0``
        and ``Psi_j`` along ``+j``. ``Psi_ij`` is the corner reached by stepping
        along ``i`` then ``j``.
    delta_i, delta_j:
        Finite-difference displacements along the ``i`` and ``j`` directions.
    use_pt_gauge:
        If ``True`` (default) each neighbouring state is rephased relative to its
        predecessor so that intermediate overlaps are real and non-negative. This
        stabilises the accumulated phase.

    Returns
    -------
    tuple[float, dict]
        The curvature estimate and diagnostic statistics. The stats dictionary
        contains ``min_overlap`` (the minimum overlap magnitude encountered along
        the loop) and ``overlaps`` (a mapping from segment labels to magnitudes).
    """

    psi0 = _as_complex_array(Psi0)
    psi_i = _as_complex_array(Psi_i)
    psi_ij = _as_complex_array(Psi_ij)
    psi_j = _as_complex_array(Psi_j)

    _validate_shapes((psi0, psi_i, psi_ij, psi_j))

    delta_i_val = float(delta_i)
    delta_j_val = float(delta_j)

    if not np.isfinite(delta_i_val) or delta_i_val == 0.0:
        raise ValueError("delta_i must be a finite, non-zero scalar.")
    if not np.isfinite(delta_j_val) or delta_j_val == 0.0:
        raise ValueError("delta_j must be a finite, non-zero scalar.")

    states = [psi0, psi_i, psi_ij, psi_j]
    if use_pt_gauge:
        states = _parallel_transport_chain(states)

    overlap_magnitudes: dict[str, float] = {}
    phase_components: dict[str, float] = {}
    log_magnitudes: dict[str, float] = {}

    min_overlap = np.inf
    total_phase = 0.0

    for label, overlap in _compute_loop_overlaps(states):
        magnitude = float(np.abs(overlap))
        overlap_magnitudes[label] = magnitude
        phase = float(np.angle(overlap))
        phase_components[label] = phase
        log_magnitudes[label] = float(np.log(magnitude)) if magnitude > 0.0 else float("-inf")
        total_phase += phase
        if magnitude < min_overlap:
            min_overlap = magnitude

    argW = float(np.angle(np.exp(1j * total_phase)))
    omega = argW / (delta_i_val * delta_j_val)

    stats = {
        "min_overlap": float(min_overlap),
        "overlaps": overlap_magnitudes,
        "phases": phase_components,
        "log_overlaps": log_magnitudes,
    }

    return float(omega), stats


__all__ = ["curvature_tile"]
