from __future__ import annotations

import argparse
import json
from pathlib import Path

from cwt.cgt.analysis.phase36_analysis import run_phase36_analysis


def main() -> int:
    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description="Run Phase 36 local superoperator area-channel analysis.",
    )
    parser.add_argument("--project-root", type=Path, default=project_root)
    parser.add_argument("--output-root", type=Path, default=None)
    args = parser.parse_args()

    payload = run_phase36_analysis(
        project_root=args.project_root,
        output_root=args.output_root,
    )
    print(json.dumps(payload["switch_metrics"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
