#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

CODE_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = CODE_ROOT / 'src'
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from cwt.cgt.branch_jumps import branch_jump_payload


def _relative(report_path: Path, target_path: Path) -> str:
    return Path(os.path.relpath(target_path, start=report_path.parent)).as_posix()


def _load_scan(output_root: Path) -> dict:
    path = output_root / 'benchmark_F_bistable_line' / 'benchmark_f_scan.json'
    with path.open() as fh:
        return json.load(fh)


def _plot_branch_map(scan: dict, outpath: Path) -> None:
    mapping = {'left': -1.0, 'ambiguous': 0.0, 'right': 1.0}
    labels = scan['branch_continuation']['persistent_branch_id_map']
    arr = np.asarray([[mapping.get(item, 0.0) for item in row] for row in labels], dtype=float)
    grid_u = np.asarray(scan['grid_u'], dtype=float)
    grid_v = np.asarray(scan['grid_v'], dtype=float)
    extent = [float(grid_v[0]), float(grid_v[-1]), float(grid_u[0]), float(grid_u[-1])]
    fig, ax = plt.subplots(figsize=(6.0, 5.0))
    image = ax.imshow(arr, origin='lower', aspect='auto', extent=extent, vmin=-1.0, vmax=1.0)
    ax.set_xlabel(scan['control_names'][1])
    ax.set_ylabel(scan['control_names'][0])
    ax.set_title('Benchmark F persistent branch map')
    cbar = fig.colorbar(image, ax=ax)
    cbar.set_label('left / ambiguous / right')
    fig.tight_layout()
    fig.savefig(outpath, dpi=160)
    plt.close(fig)


def _plot_switch_counts(payload: dict, outpath: Path) -> None:
    labels = [f"{tuple(row['center'])}\nL={row['side_length']:.2f}" for row in payload['pair_rows']]
    values = np.asarray([row['switch_count_total'] for row in payload['pair_rows']], dtype=float)
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    ax.bar(np.arange(len(values)), values)
    ax.set_xticks(np.arange(len(values)))
    ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
    ax.set_ylabel('total switch count in pair')
    ax.set_title('Benchmark F loop-pair switch counts')
    fig.tight_layout()
    fig.savefig(outpath, dpi=160)
    plt.close(fig)


def _plot_pair_status(payload: dict, outpath: Path) -> None:
    trusted = payload['summary']['trusted_pair_count']
    excluded = payload['summary']['excluded_pair_count']
    r4 = payload['summary']['r4_pair_count']
    fig, ax = plt.subplots(figsize=(5.2, 4.4))
    ax.bar(['trusted', 'excluded', 'R4'], [trusted, excluded, r4])
    ax.set_ylabel('pair count')
    ax.set_title('Benchmark F pair-status summary')
    fig.tight_layout()
    fig.savefig(outpath, dpi=160)
    plt.close(fig)


def _write_report(payload: dict, report_path: Path, plots: dict[str, Path]) -> None:
    lines: list[str] = []
    lines.append('# CWT-CGT benchmark F branch-jump report')
    lines.append('')
    lines.append('This report covers the explicit branch-jump lane for the bistable benchmark. The purpose of this benchmark is to expose R4 behavior and make exclusion logic measurable rather than implicit.')
    lines.append('')
    atlas = payload['scan_branch_atlas']
    lines.append('## Atlas summary')
    lines.append('')
    lines.append(f"- Persistent branch counts: {atlas['persistent_branch_counts']}")
    lines.append(f"- Chosen branch counts: {atlas['chosen_branch_counts']}")
    lines.append(f"- Switch tiles: {atlas['switch_tile_count']}")
    lines.append(f"- Ambiguous tiles: {atlas['ambiguous_tile_count']}")
    lines.append('')
    lines.append('## Pair summary')
    lines.append('')
    lines.append(f"- Pair count: {payload['summary']['pair_count']}")
    lines.append(f"- Trusted pairs: {payload['summary']['trusted_pair_count']}")
    lines.append(f"- Excluded pairs: {payload['summary']['excluded_pair_count']}")
    lines.append(f"- R4 pairs: {payload['summary']['r4_pair_count']}")
    lines.append(f"- Switch-count summary: {payload['summary']['switch_count_total_summary']}")
    lines.append('')
    lines.append('## Pair rows')
    lines.append('')
    for row in payload['pair_rows']:
        lines.append(
            f"- center={tuple(row['center'])}, side={row['side_length']:.2f}, trusted={row['pair_trusted_r1']}, R4={row['pair_r4']}, switches={row['switch_count_total']}, excluded_reason={row['excluded_reason']}"
        )
    lines.append('')
    lines.append('## Plots')
    lines.append('')
    for key in ['branch_map', 'switch_counts', 'pair_status']:
        lines.append(f"![{key}]({_relative(report_path, plots[key])})")
        lines.append('')
    report_path.write_text('\n'.join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description='Run branch-jump analysis for benchmark F.')
    parser.add_argument('--benchmark', default='benchmark_f')
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--report-root', type=Path, required=True)
    args = parser.parse_args()

    payload = branch_jump_payload(args.benchmark, output_root=args.output_root)
    scan = _load_scan(args.output_root)
    plot_dir = args.report_root / 'plots' / 'branch_jumps' / args.benchmark
    plot_dir.mkdir(parents=True, exist_ok=True)
    plots = {
        'branch_map': plot_dir / 'persistent_branch_map.png',
        'switch_counts': plot_dir / 'switch_count_by_pair.png',
        'pair_status': plot_dir / 'trusted_vs_excluded_pairs.png',
    }
    _plot_branch_map(scan, plots['branch_map'])
    _plot_switch_counts(payload, plots['switch_counts'])
    _plot_pair_status(payload, plots['pair_status'])
    _write_report(payload, args.report_root / 'CWT-CGT_Benchmark_F_Branch_Jump_Report_v2.md', plots)


if __name__ == '__main__':
    main()
