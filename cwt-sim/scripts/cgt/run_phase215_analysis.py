from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis._utils import nan_to_none
from cwt.cgt.analysis.phase215_analysis import run_phase215_analysis


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    payload = run_phase215_analysis(project_root=project_root)
    print(json.dumps(nan_to_none(payload), indent=2))


if __name__ == '__main__':
    main()
