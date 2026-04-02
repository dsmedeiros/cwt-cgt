from __future__ import annotations

import argparse
import json
from pathlib import Path

from cwt.cgt.analysis.phase37_analysis import Phase37Config, run_phase37_analysis


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description="Run Phase 37 local-superoperator-compactness analysis.",
    )
    parser.add_argument("--project-root", type=Path, default=project_root)
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument("--switch-gamma", type=float, default=0.30)
    args = parser.parse_args()

    payload = run_phase37_analysis(
        project_root=args.project_root,
        output_root=args.output_root,
        config=Phase37Config(default_switch_gamma=args.switch_gamma),
    )
    print(json.dumps(payload["switch_metrics"], indent=2))


if __name__ == "__main__":
    main()
