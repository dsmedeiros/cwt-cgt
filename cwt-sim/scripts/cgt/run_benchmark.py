from __future__ import annotations

import argparse
from pathlib import Path

from cwt.cgt.models import ScanConfig
from cwt.cgt.runner import run_benchmark_scan


def main() -> None:
    parser = argparse.ArgumentParser(description='Run a CWT-CGT benchmark scan.')
    parser.add_argument('--benchmark', required=True, choices=['benchmark_a', 'benchmark_b', 'benchmark_c', 'benchmark_d'])
    parser.add_argument('--mesh', type=int, default=9)
    parser.add_argument('--output-root', type=Path, default=Path(__file__).resolve().parents[2] / '03_benchmarks' / 'results')
    args = parser.parse_args()

    config = ScanConfig(mesh=args.mesh)
    payload = run_benchmark_scan(args.benchmark, output_root=args.output_root, config=config)
    print(f"Completed {payload['benchmark']} with regime summary: {payload['regime_summary']}")
    print(f"Wrote results under: {args.output_root}")


if __name__ == '__main__':
    main()
