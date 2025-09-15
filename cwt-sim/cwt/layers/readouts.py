"""Placeholder readout functions for layer outputs."""

from __future__ import annotations

from .state import LayerState


def compute_readout(state: LayerState) -> dict[str, object]:
    """Produce a trivial readout dictionary for the given state."""
    return {"payload": state.payload}
