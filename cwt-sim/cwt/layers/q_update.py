"""Placeholder Q-layer update routines."""

from __future__ import annotations

from .state import LayerState


def update_q(state: LayerState) -> LayerState:
    """Return the state unchanged as a stand-in for the real update."""
    return state
