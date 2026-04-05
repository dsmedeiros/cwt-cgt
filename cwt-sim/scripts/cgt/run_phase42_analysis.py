from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none
from cwt.cgt.analysis.phase42_analysis import run_phase42_analysis


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    payload = run_phase42_analysis(project_root=project_root, output_root=project_root)
    print(json.dumps(nan_to_none(payload['switch_metrics']), indent=2))


if __name__ == '__main__':
    main()
