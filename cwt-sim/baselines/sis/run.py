"""CLI for the Susceptible-Infected-Susceptible (SIS) baseline."""
from __future__ import annotations

import argparse
from typing import List, Optional

from baselines.common import (
    BaselineRunConfig,
    build_shared_parser,
    namespace_to_config,
)


def get_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the SIS driver."""

    return build_shared_parser(
        "SIS baseline simulation driver.",
        (
            ("--infection-rate",),
            {
                "type": float,
                "default": 0.1,
                "help": "Infection probability for each contact.",
            },
        ),
    )


def main(argv: Optional[List[str]] = None) -> BaselineRunConfig:
    """Parse CLI arguments and return the resulting configuration."""

    parser = get_parser()
    namespace = parser.parse_args(argv)
    config = namespace_to_config(namespace)

    if argv is None:
        print("SIS baseline execution is not yet implemented.")

    return config


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
