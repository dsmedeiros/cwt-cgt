from __future__ import annotations

import argparse
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
SRC_ROOT = PROJECT_ROOT / '04_code' / 'src'
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from cwt.cgt.phase12_analysis import phase12_payload, phase12_report


def main() -> None:
    parser = argparse.ArgumentParser(description='Run Phase 12 dense mixed-state phase-convention analysis.')
    parser.add_argument('--output-root', type=Path, default=PROJECT_ROOT / '03_benchmarks' / 'results')
    args = parser.parse_args()

    payload = phase12_payload(output_root=args.output_root)
    outputs = phase12_report(output_root=args.output_root, payload=payload)
    print('Phase 12 analysis complete.')
    for key, path in outputs.items():
        print(f'{key}: {path}')


if __name__ == '__main__':
    main()
