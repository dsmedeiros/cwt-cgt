#!/usr/bin/env python3
from __future__ import annotations

import argparse
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

from cwt.cgt.noisy import NoisyConfig, noisy_benchmark_payload


def _relative(report_path: Path, target_path: Path) -> str:
    import os
    return Path(os.path.relpath(target_path, start=report_path.parent)).as_posix()


def _plot_coherence(levels: list[dict], outpath: Path) -> None:
    gamma = np.asarray([level['dephasing'] for level in levels], dtype=float)
    mean_coh = np.asarray([level['coherence_ratio_summary']['mean'] for level in levels], dtype=float)
    fig, ax = plt.subplots(figsize=(6.4, 4.8))
    ax.plot(gamma, mean_coh, marker='o')
    ax.set_xlabel('dephasing γ')
    ax.set_ylabel('mean loop coherence ratio')
    ax.set_title('Noisy lane: coherence ratio vs dephasing')
    fig.tight_layout()
    fig.savefig(outpath, dpi=160)
    plt.close(fig)


def _plot_patchwise_gap_slopes(levels: list[dict], outpath: Path) -> None:
    centers = [tuple(item['center']) for item in levels[0]['by_center']]
    fig, ax = plt.subplots(figsize=(6.4, 4.8))
    for center in centers:
        gamma = []
        slopes = []
        for level in levels:
            for item in level['by_center']:
                if tuple(item['center']) == center:
                    gamma.append(level['dephasing'])
                    slopes.append(item['fit_orientation_gap_vs_abs_flux']['slope'])
        ax.plot(np.asarray(gamma, dtype=float), np.asarray(slopes, dtype=float), marker='o', label=f'center={center}')
    ax.set_xlabel('dephasing γ')
    ax.set_ylabel('patchwise gap-vs-|flux| slope')
    ax.set_title('Noisy lane: patchwise orientation-gap slopes')
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(outpath, dpi=160)
    plt.close(fig)


def _plot_bures_metric(scan_levels: list[dict], outpath: Path) -> None:
    gamma = np.asarray([level['dephasing'] for level in scan_levels], dtype=float)
    mean_metric = np.asarray([level['bures_metric_summary']['mean'] for level in scan_levels], dtype=float)
    fig, ax = plt.subplots(figsize=(6.4, 4.8))
    ax.plot(gamma, mean_metric, marker='o')
    ax.set_xlabel('dephasing γ')
    ax.set_ylabel('mean Bures metric trace')
    ax.set_title('Noisy lane: Bures metric summary vs dephasing')
    fig.tight_layout()
    fig.savefig(outpath, dpi=160)
    plt.close(fig)


def _plot_example_pairs(levels: list[dict], outpath: Path) -> None:
    baseline = levels[0]
    switchish = levels[min(3, len(levels) - 1)]
    fig, ax = plt.subplots(figsize=(6.4, 4.8))
    for level in [baseline, switchish]:
        x = np.asarray([row['flux_magnitude'] for row in level['pairs']], dtype=float)
        y = np.asarray([row['orientation_gap'] for row in level['pairs']], dtype=float)
        ax.scatter(x, y, label=f"γ={level['dephasing']:.2f}")
    ax.set_xlabel('|signed flux|')
    ax.set_ylabel('orientation gap')
    ax.set_title('Noisy lane: orientation gap vs |flux|')
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(outpath, dpi=160)
    plt.close(fig)


def _write_report(payload: dict, report_path: Path, plots: dict[str, Path]) -> None:
    lines: list[str] = []
    lines.append('# CWT-CGT noisy / CPTP benchmark report')
    lines.append('')
    lines.append('This report covers the explicit noisy lane for the ring benchmark. The implemented dynamics is a CPTP relaxation/dephasing/depolarizing scaffold, not yet a full microscopic open-system derivation.')
    lines.append('')
    lines.append(f"- Benchmark: {payload['benchmark']}")
    lines.append(f"- Recommended mixed-state switch dephasing: {payload['recommended_switch_dephasing']:.2f}")
    lines.append(f"- Switch rule: {payload['switch_rule']}")
    lines.append('')
    lines.append('## Loop-side patchwise fits')
    lines.append('')
    for level in payload['loop_levels']:
        lines.append(f"### γ = {level['dephasing']:.2f}")
        lines.append('')
        lines.append(f"- Global fit (orientation gap vs |flux|): slope = {level['fit_orientation_gap_vs_abs_flux']['slope']}, R² = {level['fit_orientation_gap_vs_abs_flux']['r2']}")
        lines.append(f"- Mean coherence ratio = {level['coherence_ratio_summary']['mean']}")
        for item in level['by_center']:
            fit = item['fit_orientation_gap_vs_abs_flux']
            lines.append(f"- Center {tuple(item['center'])}: slope = {fit['slope']}, R² = {fit['r2']}")
        lines.append('')
    lines.append('## Plots')
    lines.append('')
    for key in ['coherence_vs_dephasing', 'patchwise_slopes', 'bures_metric', 'orientation_gap_examples']:
        lines.append(f"![{key}]({_relative(report_path, plots[key])})")
        lines.append('')
    report_path.write_text('\n'.join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description='Run noisy/CPTP benchmark analysis.')
    parser.add_argument('--benchmark', default='benchmark_c')
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--report-root', type=Path, required=True)
    args = parser.parse_args()

    payload = noisy_benchmark_payload(args.benchmark, output_root=args.output_root, noisy_config=NoisyConfig())
    plot_dir = args.report_root / 'plots' / 'noisy' / args.benchmark
    plot_dir.mkdir(parents=True, exist_ok=True)
    plots = {
        'coherence_vs_dephasing': plot_dir / 'coherence_vs_dephasing.png',
        'patchwise_slopes': plot_dir / 'patchwise_gap_slopes_vs_dephasing.png',
        'bures_metric': plot_dir / 'bures_metric_vs_dephasing.png',
        'orientation_gap_examples': plot_dir / 'orientation_gap_vs_abs_flux_examples.png',
    }
    _plot_coherence(payload['loop_levels'], plots['coherence_vs_dephasing'])
    _plot_patchwise_gap_slopes(payload['loop_levels'], plots['patchwise_slopes'])
    _plot_bures_metric(payload['scan_levels'], plots['bures_metric'])
    _plot_example_pairs(payload['loop_levels'], plots['orientation_gap_examples'])
    _write_report(payload, args.report_root / 'CWT-CGT_Noisy_Benchmark_C_Report.md', plots)


if __name__ == '__main__':
    main()
