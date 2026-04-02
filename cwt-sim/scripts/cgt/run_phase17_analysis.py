from __future__ import annotations

import json
from pathlib import Path

from cwt.cgt.analysis.phase17_analysis import Phase17Config, phase17_payload, phase17_report


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    output_root = project_root / 'cgt_benchmarks' / 'results'
    payload = phase17_payload(output_root=output_root, phase17_config=Phase17Config())
    plots = phase17_report(output_root=output_root, payload=payload)
    print(
        json.dumps(
            {
                'phase17_payload': str((project_root / 'cgt_benchmarks' / 'reports' / 'phase17_summary.json')),
                'plots': {key: str(path) for key, path in plots.items()},
            },
            indent=2,
        )
    )


if __name__ == '__main__':
    main()
