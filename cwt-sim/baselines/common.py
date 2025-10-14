"""Shared CLI utilities for baseline simulation drivers."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np

from .io import DEFAULT_AXIS_MAP_PATH, load_axis_map


@dataclass(slots=True)
class BaselineRunConfig:
    """Container capturing the shared CLI parameters for baseline models."""

    axis_map: Path
    output_dir: Path | None
    steps: int
    seed: int | None
    time_budget: float
    map_to_cwt: bool = True


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
        default=64,
        help=(
            "Number of discrete simulation steps to evaluate (default: %(default)s)."
            " Defaults are tuned so the reference sweeps fit within a 60 s budget."
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help=(
            "Seed for deterministic pseudo-random behavior when supported by the model"
            " (default: %(default)s)."
        ),
    )
    parser.add_argument(
        "--time-budget",
        type=float,
        default=60.0,
        help=(
            "Maximum runtime in seconds before emitting a warning (default: %(default)s)."
            " The budget is enforced via time_budget_guard without aborting the sweep."
        ),
    )
    parser.add_argument(
        "--map-to-cwt",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "When disabled, skip canonical axis remapping and emphasise proxy curvature "
            "estimates alongside intrinsic |Ω| values (default: %(default)s)."
        ),
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
        time_budget=namespace.time_budget,
        map_to_cwt=namespace.map_to_cwt,
    )


def combine_proxy_magnitudes(magnitudes: Sequence[np.ndarray]) -> np.ndarray:
    """Combine multiple proxy gradient magnitudes into a single envelope."""

    if not magnitudes:
        raise ValueError("At least one magnitude array is required")

    prepared = [np.asarray(entry, dtype=float) for entry in magnitudes]
    stacked = np.stack([np.nan_to_num(entry, nan=-np.inf) for entry in prepared], axis=0)
    envelope = np.max(stacked, axis=0)
    envelope[np.isneginf(envelope)] = np.nan
    envelope[~np.isfinite(envelope)] = np.nan
    return envelope
