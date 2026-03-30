from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use('Agg')

from cwt.cgt.analysis.phase14_analysis import Phase14Config, phase14_payload, phase14_report


def main() -> None:
    parser = argparse.ArgumentParser(description='Run Phase 14 smoothed local mixed-state field analysis.')
    parser.add_argument('--output-root', type=Path, default=Path(__file__).resolve().parents[2] / 'cgt_benchmarks' / 'results')
    args = parser.parse_args()

    payload = phase14_payload(output_root=args.output_root, phase14_config=Phase14Config())
    outputs = phase14_report(output_root=args.output_root, payload=payload)
    print('Phase 14 analysis complete.')
    for key, path in outputs.items():
        print(f'{key}: {path}')


if __name__ == '__main__':
    main()
