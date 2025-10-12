"""Shared CLI utilities for baseline simulation drivers."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from .io import DEFAULT_AXIS_MAP_PATH


@dataclass(slots=True)
class BaselineRunConfig:
    """Container capturing the shared CLI parameters for baseline models."""

    axis_map: Path
    output_dir: Path | None
    steps: int
    seed: int | None


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
