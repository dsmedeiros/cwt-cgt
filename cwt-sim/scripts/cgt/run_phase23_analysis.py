from __future__ import annotations

import argparse
import json
from pathlib import Path

from cwt.cgt.analysis.phase23_analysis import Phase23Config, phase23_payload


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description="Run Phase 23 broader held-out transfer analysis.",
    )
    parser.add_argument("--project-root", type=Path, default=project_root)
    parser.add_argument("--output-json", type=Path, default=None)
    args = parser.parse_args()

    payload = phase23_payload(project_root=args.project_root, config=Phase23Config())
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(payload, indent=2))
    else:
        print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
