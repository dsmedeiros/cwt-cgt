from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis.phase29_analysis import Phase29Config, run_phase29_analysis


def main() -> int:
    project_root = Path(__file__).resolve().parents[2]
    payload = run_phase29_analysis(
        project_root=project_root,
        output_root=project_root,
        config=Phase29Config(),
    )
    print(
        json.dumps(
            {
                "phase": payload["phase"],
                "benchmark": payload["benchmark"],
                "switch_gamma": payload["switch_gamma"],
                "switch_metrics": payload["switch_metrics"],
                "verdict": payload["verdict"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
