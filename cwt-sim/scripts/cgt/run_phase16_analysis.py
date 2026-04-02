from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis.phase16_analysis import Phase16Config, phase16_payload, phase16_report


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    output_root = project_root / "cgt_benchmarks" / "results"
    reports_dir = project_root / "cgt_benchmarks" / "reports"
    payload = phase16_payload(output_root=output_root, phase16_config=Phase16Config())
    plots = phase16_report(output_root=output_root, payload=payload)
    print(
        json.dumps(
            {
                "phase16_payload": str(reports_dir / "phase16_summary.json"),
                "plots": {key: str(path) for key, path in plots.items()},
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
