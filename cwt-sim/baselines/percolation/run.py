"""CLI for the percolation model baseline."""
from __future__ import annotations

import argparse
from typing import List, Optional

from baselines.common import (
    BaselineRunConfig,
    build_shared_parser,
    namespace_to_config,
)


def get_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the percolation driver."""

    return build_shared_parser(
        "Percolation baseline simulation driver.",
        (
            ("--occupation-probability",),
            {
                "type": float,
                "default": 0.5,
                "help": "Probability of each edge being occupied.",
            },
        ),
    )


def main(argv: Optional[List[str]] = None) -> BaselineRunConfig:
    """Parse CLI arguments and return the resulting configuration."""

    parser = get_parser()
    namespace = parser.parse_args(argv)
    config = namespace_to_config(namespace)

    if argv is None:
        print("Percolation baseline execution is not yet implemented.")

    return config


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
