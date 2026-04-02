from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis.phase28_analysis import phase28_payload


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    payload = phase28_payload(project_root)
    print(json.dumps(payload["switch_metrics"], indent=2))


if __name__ == "__main__":
    main()
