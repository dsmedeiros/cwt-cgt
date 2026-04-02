from __future__ import annotations

import argparse
from pathlib import Path

from cwt.cgt.analysis.phase33_analysis import Phase33Config, run_phase33_analysis


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description="Run Phase 33 local superoperator geometry clip analysis.",
    )
    parser.add_argument("--project-root", type=Path, default=project_root)
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument("--switch-gamma", type=float, default=0.30)
    args = parser.parse_args()

    payload = run_phase33_analysis(
        project_root=args.project_root,
        output_root=args.output_root,
        config=Phase33Config(default_switch_gamma=args.switch_gamma),
    )
    print(payload["verdict"])


if __name__ == "__main__":
    main()
