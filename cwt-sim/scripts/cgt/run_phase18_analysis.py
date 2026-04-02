from __future__ import annotations

import argparse
import json
from pathlib import Path

from cwt.cgt.analysis.phase18_analysis import Phase18Config, phase18_payload


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description="Run Phase 18 analytic branch-tangent field analysis.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=project_root / "cgt_benchmarks" / "results",
    )
    parser.add_argument("--scan-mesh", type=int, default=7)
    args = parser.parse_args()

    payload = phase18_payload(
        output_root=args.output_root,
        cfg=Phase18Config(scan_mesh=args.scan_mesh),
    )
    report_dir = project_root / "cgt_benchmarks" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "phase18_summary.json").write_text(json.dumps(payload, indent=2))
    print(
        json.dumps(
            {"phase": payload["phase"], "focus_benchmark": payload["focus_benchmark"]},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
