"""Baseline model entry points for the cwt-sim project."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

from .common import BaselineRunConfig, add_shared_cli_arguments, build_shared_parser
from .io import DEFAULT_AXIS_MAP_PATH, load_axis_map

__all__ = [
    "BaselineRunConfig",
    "DEFAULT_AXIS_MAP_PATH",
    "add_shared_cli_arguments",
    "build_shared_parser",
    "load_axis_map",
]


def __getattr__(name: str):
    """Dynamically expose model subpackages without importing them eagerly."""
    if name in {"kuramoto", "ising", "percolation", "sis"}:
        return import_module(f"{__name__}.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if TYPE_CHECKING:  # pragma: no cover - for static analyzers only
    from . import ising, kuramoto, percolation, sis  # noqa: F401
