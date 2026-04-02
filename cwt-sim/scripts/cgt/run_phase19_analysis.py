from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis.phase19_analysis import phase19_payload


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    output_root = project_root / "cgt_benchmarks" / "results"
    payload = phase19_payload(output_root=output_root)
    reports_dir = project_root / "cgt_benchmarks" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    target = reports_dir / "phase19_summary.json"
    target.write_text(json.dumps(payload, indent=2))
    print(target)


if __name__ == "__main__":
    main()
