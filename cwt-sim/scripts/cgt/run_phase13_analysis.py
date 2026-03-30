from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use('Agg')

from cwt.cgt.analysis.phase13_analysis import Phase13Config, phase13_payload, phase13_report


def main() -> None:
    parser = argparse.ArgumentParser(description='Run Phase 13 local mixed-state atlas analysis.')
    parser.add_argument('--output-root', type=Path, default=Path(__file__).resolve().parents[2] / 'cgt_benchmarks' / 'results')
    args = parser.parse_args()

    payload = phase13_payload(output_root=args.output_root, phase13_config=Phase13Config())
    outputs = phase13_report(output_root=args.output_root, payload=payload)
    print('Phase 13 analysis complete.')
    for key, path in outputs.items():
        print(f'{key}: {path}')


if __name__ == '__main__':
    main()
