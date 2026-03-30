"""Thin compatibility shim re-exporting geometry helpers for CGT modules."""

from __future__ import annotations

from cwt.geometry.berry import (
    berry_loop_flux,
    polygon_signed_area,
    psi_from_parts,
    psi_from_state,
)
from cwt.geometry.branch_distance import branch_distance
from cwt.geometry.coherence import (
    canonicalize_phase,
    normalize_probabilities,
    phase_coherence,
    projective_metric_trace_and_curvature,
    wrap_phase,
)
from cwt.geometry.psi import inner as _inner
from cwt.geometry.stats import summarize, summarize_abs


def overlap(psi_a, psi_b) -> float:
    """Fidelity overlap |<a|b>| between two state vectors."""
    return float(abs(_inner(psi_a, psi_b)))


__all__ = [
    "psi_from_parts",
    "psi_from_state",
    "overlap",
    "normalize_probabilities",
    "wrap_phase",
    "canonicalize_phase",
    "phase_coherence",
    "projective_metric_trace_and_curvature",
    "berry_loop_flux",
    "polygon_signed_area",
    "branch_distance",
    "summarize",
    "summarize_abs",
]
