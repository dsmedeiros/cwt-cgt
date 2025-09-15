"""State containers used across Q, Θ, and C layers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class LayerState:
    """Minimal placeholder structure for layer state."""

    payload: Any | None = None
