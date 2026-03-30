from __future__ import annotations

import argparse
import sys
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = CODE_ROOT / 'src'
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from cwt.cgt.benchmarks import BENCHMARKS
from cwt.cgt.robustness import run_robustness_suite


def main() -> None:
    parser = argparse.ArgumentParser(description='Run the held-out loop-family/off-center robustness suite.')
    parser.add_argument('--benchmark', required=True, choices=sorted(BENCHMARKS))
    parser.add_argument('--output-root', type=Path, default=Path(__file__).resolve().parents[2] / '03_benchmarks' / 'results')
    args = parser.parse_args()

    payload = run_robustness_suite(args.benchmark, output_root=args.output_root)
    print(f"Completed robustness suite for {payload['benchmark']} -> {payload['summary']['passed_protocol_count']}/{payload['summary']['protocol_count']} protocols passed")


if __name__ == '__main__':
    main()
