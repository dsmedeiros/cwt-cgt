from __future__ import annotations

import argparse
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
SRC_ROOT = PROJECT_ROOT / '04_code' / 'src'
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from cwt.cgt.phase11_analysis import phase11_payload, phase11_report


def main() -> None:
    parser = argparse.ArgumentParser(description='Run Phase 11 continuous-time Lindblad analysis.')
    parser.add_argument('--output-root', type=Path, default=PROJECT_ROOT / '03_benchmarks' / 'results')
    args = parser.parse_args()

    payload = phase11_payload(output_root=args.output_root)
    outputs = phase11_report(output_root=args.output_root, payload=payload)
    print('Phase 11 analysis complete.')
    for key, path in outputs.items():
        print(f'{key}: {path}')


if __name__ == '__main__':
    main()
