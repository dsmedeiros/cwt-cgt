"""Noise models including dephasing, amplitude, and delay jitter."""

from __future__ import annotations


def placeholder_noise_model() -> dict[str, float]:
    """Return placeholder parameters for a noise model."""
    return {"dephasing": 0.0, "amplitude": 0.0, "jitter": 0.0}
