from __future__ import annotations

import argparse
import json
from pathlib import Path

from cwt.cgt.analysis.phase27_analysis import Phase27Config, phase27_payload


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description="Run CWT-CGT Phase 27 moment-normalizer analysis.",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=project_root,
        help="Path to the project root",
    )
    parser.add_argument(
        "--switch-gamma",
        type=float,
        default=0.30,
        help="Preferred switch dephasing for summary selection",
    )
    args = parser.parse_args()

    payload = phase27_payload(
        args.project_root,
        config=Phase27Config(default_switch_gamma=args.switch_gamma),
    )
    print(json.dumps(payload["switch_metrics"], indent=2))


if __name__ == "__main__":
    main()
