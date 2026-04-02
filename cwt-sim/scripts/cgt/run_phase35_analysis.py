from __future__ import annotations

import argparse
from pathlib import Path

from cwt.cgt.analysis.phase35_analysis import run_phase35_analysis


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description="Run Phase 35 local superoperator geometry-baseline analysis.",
    )
    parser.add_argument("--project-root", type=Path, default=project_root)
    parser.add_argument("--output-root", type=Path, default=None)
    args = parser.parse_args()

    payload = run_phase35_analysis(args.project_root, args.output_root)
    print(payload["phase"])
    print(payload["switch_metrics"])


if __name__ == "__main__":
    main()
