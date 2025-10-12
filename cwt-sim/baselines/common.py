"""Shared CLI utilities for baseline simulation drivers."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from .io import DEFAULT_AXIS_MAP_PATH, load_axis_map


@dataclass(slots=True)
class BaselineRunConfig:
    """Container capturing the shared CLI parameters for baseline models."""

    axis_map: Path
    output_dir: Path | None
    steps: int
    seed: int | None


_AXIS_MAP_CACHE: Mapping[str, object] | None = None


def _load_axis_map_cache() -> Mapping[str, object]:
    global _AXIS_MAP_CACHE

    if _AXIS_MAP_CACHE is None:
        _AXIS_MAP_CACHE = load_axis_map(DEFAULT_AXIS_MAP_PATH)
    return _AXIS_MAP_CACHE


def map_axes(model_axes: dict[str, float], model_name: str) -> dict[str, float]:
    """Translate model-specific axis names to the canonical CWT terminology."""

    if not model_name:
        raise ValueError("model_name must be a non-empty string")

    mapping = _load_axis_map_cache()
    models_section = mapping.get("models")
    if not isinstance(models_section, Mapping):
        raise KeyError("Axis map is missing the 'models' section")

    try:
        model_entry = models_section[model_name]
    except KeyError as exc:  # pragma: no cover - defensive guard
        raise KeyError(f"Axis map has no entry for model '{model_name}'") from exc

    axes_section = model_entry.get("axes") if isinstance(model_entry, Mapping) else None
    if not isinstance(axes_section, Mapping):
        raise KeyError(f"Axis map entry for model '{model_name}' is missing 'axes'")

    mapped: dict[str, float] = {}
    for cwt_axis, model_axis in axes_section.items():
        if not isinstance(model_axis, str):
            raise TypeError(f"Axis map for model '{model_name}' must map to string axis names")
        if model_axis not in model_axes:
            raise KeyError(f"Model axes are missing required key '{model_axis}' for '{model_name}'")
        mapped[str(cwt_axis)] = float(model_axes[model_axis])

    return mapped


def add_shared_cli_arguments(parser: argparse.ArgumentParser) -> None:
    """Register CLI arguments that are common to every baseline model."""

    parser.add_argument(
        "--axis-map",
        type=Path,
        default=DEFAULT_AXIS_MAP_PATH,
        help="Path to an axis map YAML file used to align output arrays.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional directory where derived artifacts should be written.",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=100,
        help="Number of discrete simulation steps to evaluate (default: %(default)s).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Seed for deterministic pseudo-random behavior when supported by the model.",
    )


def build_shared_parser(
    description: str,
    *extra_arguments: Iterable[tuple[Sequence[str], dict[str, object]]],
) -> argparse.ArgumentParser:
    """Create a parser with shared arguments and optional model specific extras."""

    parser = argparse.ArgumentParser(description=description)
    add_shared_cli_arguments(parser)
    for argument_group in extra_arguments:
        flags, kwargs = argument_group
        parser.add_argument(*flags, **kwargs)
    return parser


def namespace_to_config(namespace: argparse.Namespace) -> BaselineRunConfig:
    """Translate a parsed :class:`argparse.Namespace` into a configuration object."""

    return BaselineRunConfig(
        axis_map=namespace.axis_map,
        output_dir=namespace.output_dir,
        steps=namespace.steps,
        seed=namespace.seed,
    )
