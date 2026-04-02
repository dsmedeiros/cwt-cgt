from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis.phase21_analysis import Phase21Config, phase21_payload


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    output_root = project_root / "cgt_benchmarks" / "results"
    payload = phase21_payload(output_root=output_root, phase21_config=Phase21Config())
    out_path = project_root / "cgt_benchmarks" / "reports" / "phase21_summary.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2))
    print(out_path)


if __name__ == "__main__":
    main()
