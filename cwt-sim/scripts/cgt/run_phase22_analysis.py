from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis.phase22_analysis import phase22_payload


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    payload = phase22_payload(project_root)
    print(
        json.dumps(
            {
                "phase": payload["phase"],
                "benchmark": payload["benchmark"],
                "switch_gamma": payload["switch_gamma"],
                "verdict": payload["verdict"],
                "heldout_r2_switch": payload["switch_level"]["heldout_fit"]["r2"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
