from __future__ import annotations

import argparse
import json
from pathlib import Path

from cwt.cgt.analysis.phase20_analysis import Phase20Config, phase20_payload


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description="Run Phase 20 path-order correction analysis.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=project_root / "cgt_benchmarks" / "results",
    )
    parser.add_argument("--scan-mesh", type=int, default=7)
    args = parser.parse_args()

    payload = phase20_payload(
        args.output_root,
        phase20_config=Phase20Config(scan_mesh=args.scan_mesh),
    )
    print(json.dumps(payload["focus_switch_summary"], indent=2))


if __name__ == "__main__":
    main()
