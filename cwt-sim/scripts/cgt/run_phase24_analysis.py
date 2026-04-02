from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis.phase24_analysis import phase24_payload


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    payload = phase24_payload(project_root=project_root)
    print(
        json.dumps(
            {
                "benchmark": payload["benchmark"],
                "verdict": payload["verdict"],
                "switch_gamma": payload["switch_gamma"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
