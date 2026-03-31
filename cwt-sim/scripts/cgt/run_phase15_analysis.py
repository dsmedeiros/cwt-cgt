from __future__ import annotations

import argparse
import json
from pathlib import Path

from cwt.cgt.analysis.phase15_analysis import (
    Phase15Config,
    phase15_payload,
    phase15_report,
)


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description="Run Phase 15 generator-tangent field analysis.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=project_root / "cgt_benchmarks" / "results",
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=project_root / "05_reports",
    )
    args = parser.parse_args()

    payload = phase15_payload(
        output_root=args.output_root,
        phase15_config=Phase15Config(),
        reports_dir=args.reports_dir,
    )
    plots = phase15_report(output_root=args.output_root, payload=payload)
    summary_path = str(args.reports_dir / "phase15_summary.json")
    print(
        json.dumps(
            {
                "phase15_payload": summary_path,
                "plots": {
                    key: str(path) for key, path in plots.items()
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
