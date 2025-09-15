"""Configuration loading scaffolding."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def load_config(path: str | Path) -> dict[str, Any]:
    """Return an empty configuration placeholder."""
    return {"source": str(path)}
