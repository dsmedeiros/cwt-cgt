from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis.phase39_analysis import run_phase39_analysis


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    payload = run_phase39_analysis(
        project_root=project_root,
        output_root=project_root,
    )
    print(json.dumps(payload["switch_metrics"], indent=2))


if __name__ == "__main__":
    main()
