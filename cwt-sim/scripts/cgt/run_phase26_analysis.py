from __future__ import annotations

import argparse
import json
from pathlib import Path

from cwt.cgt.analysis.phase26_analysis import phase26_payload


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description="Run Phase 26 generator-normalized full-transfer analysis.",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=project_root,
        help="Path to CWT-CGT project root",
    )
    args = parser.parse_args()

    payload = phase26_payload(args.project_root)
    print(
        json.dumps(
            {
                "phase": payload["phase"],
                "verdict": payload["verdict"],
                "switch_metrics": payload["switch_metrics"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
