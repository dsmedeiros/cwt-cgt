"""I/O utilities shared across baseline models."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

DEFAULT_AXIS_MAP_PATH = Path(__file__).resolve().parent / "axis_map.yml"


def load_axis_map(path: Path | None = None) -> Mapping[str, Any]:
    """Load an axis map YAML document."""

    import yaml  # type: ignore[import-untyped]

    target = path or DEFAULT_AXIS_MAP_PATH
    with target.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}
