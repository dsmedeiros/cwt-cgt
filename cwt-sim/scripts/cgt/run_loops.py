from __future__ import annotations

import argparse
import sys
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = CODE_ROOT / 'src'
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from cwt.cgt.loop_protocols import run_benchmark_loops
from cwt.cgt.models import LoopConfig


def main() -> None:
    parser = argparse.ArgumentParser(description='Run nested clockwise/counter-clockwise CWT-CGT loop families.')
    parser.add_argument('--benchmark', required=True, choices=['benchmark_a', 'benchmark_b', 'benchmark_c', 'benchmark_d'])
    parser.add_argument('--shape', choices=['square', 'circle'], default='square')
    parser.add_argument('--steps-per-segment', type=int, default=24)
    parser.add_argument('--output-root', type=Path, default=Path(__file__).resolve().parents[2] / '03_benchmarks' / 'results')
    args = parser.parse_args()

    payload = run_benchmark_loops(
        benchmark_id=args.benchmark,
        output_root=args.output_root,
        config=LoopConfig(shape=args.shape, steps_per_segment=args.steps_per_segment),
    )
    print(f"Completed loop-family run for {payload['benchmark']} -> sign-flip fraction {payload['summary']['sign_flip_fraction_r1']:.3f}")


if __name__ == '__main__':
    main()
