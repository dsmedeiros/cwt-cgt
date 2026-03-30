#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from cwt.cgt.jacobian_analysis import benchmark_jacobian_payload


def _scatter_with_fit(x: np.ndarray, y: np.ndarray, xlabel: str, ylabel: str, title: str, outpath: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.2, 5.0))
    ax.scatter(x, y)
    if x.size and not np.allclose(x, 0.0):
        slope = float(np.dot(x, y) / np.dot(x, x))
        xs = np.linspace(float(np.min(x)), float(np.max(x)), 128)
        ax.plot(xs, slope * xs)
    ax.axhline(0.0, linewidth=0.8)
    ax.axvline(0.0, linewidth=0.8)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(outpath, dpi=160)
    plt.close(fig)


def _write_report(payloads: dict[str, dict], plot_paths: dict[str, Path], output_path: Path) -> None:
    lines: list[str] = []
    lines.append('# CWT-CGT Phase 6 Jacobian report')
    lines.append('')
    lines.append('This report summarizes the explicit branch-Jacobian upgrade. The main accepted Jacobian observable is the derived predicted signed flux, computed from Jacobian-response curvature rather than from the older auxiliary modal surrogate.')
    lines.append('')
    for benchmark_id in ['benchmark_a', 'benchmark_b', 'benchmark_c', 'benchmark_d']:
        payload = payloads[benchmark_id]
        scan = payload['scan']
        loops = payload['loops']
        lines.append(f'## {benchmark_id}')
        lines.append('')
        lines.append(f"- Scan correlation: predicted metric vs state metric = {scan['correlations']['predicted_metric_vs_state_metric']}")
        lines.append(f"- Scan correlation: predicted curvature vs state curvature = {scan['correlations']['predicted_curvature_vs_state_curvature']}")
        lines.append(f"- Loop fit: response vs predicted signed flux = {loops['summary']['fit_response_vs_predicted_signed_flux']}")
        lines.append(f"- Loop fit: predicted signed flux vs state signed flux = {loops['summary']['fit_predicted_signed_flux_vs_state_signed_flux']}")
        lines.append(f"- Secondary diagnostic: response vs Jacobian modal phase = {loops['summary']['fit_response_vs_jacobian_modal_phase']}")
        lines.append('')
        if benchmark_id == 'benchmark_c':
            patch = payload['patchwise_explanation']
            lines.append('- Patchwise reconstruction of response-vs-state-flux slope from Jacobian factors:')
            lines.append('')
            for row in patch['center_summaries']:
                lines.append(
                    f"  - center {row['center']}: observed slope = {row['mean_response_vs_state_flux_slope']}, reconstructed = {row['reconstructed_response_vs_state_flux_slope']}, relative error = {row['relative_error']}"
                )
            lines.append('')
            for key in ['response_vs_predicted_flux', 'predicted_flux_vs_state_flux', 'patchwise_reconstruction']:
                rel = plot_paths[key].relative_to(output_path.parent)
                lines.append(f'![{key}]({rel.as_posix()})')
                lines.append('')
    output_path.write_text('\n'.join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description='Run Phase 6 Jacobian analysis and generate report artifacts.')
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--report-root', type=Path, required=True)
    args = parser.parse_args()

    args.output_root.mkdir(parents=True, exist_ok=True)
    args.report_root.mkdir(parents=True, exist_ok=True)
    payloads = {bid: benchmark_jacobian_payload(bid, output_root=args.output_root) for bid in ['benchmark_a', 'benchmark_b', 'benchmark_c', 'benchmark_d']}

    c_runs = [run for run in payloads['benchmark_c']['loops']['runs'] if run['trusted_r1']]
    plot_dir = args.report_root / 'plots' / 'jacobian' / 'benchmark_c'
    plot_dir.mkdir(parents=True, exist_ok=True)
    plot_paths = {
        'response_vs_predicted_flux': plot_dir / 'response_vs_predicted_flux.png',
        'predicted_flux_vs_state_flux': plot_dir / 'predicted_flux_vs_state_flux.png',
        'patchwise_reconstruction': plot_dir / 'patchwise_reconstruction.png',
    }
    _scatter_with_fit(
        np.asarray([run['predicted_signed_flux_pathmean'] for run in c_runs], dtype=float),
        np.asarray([run['response'] for run in c_runs], dtype=float),
        'predicted signed flux',
        'response',
        'Benchmark C: response vs predicted signed flux',
        plot_paths['response_vs_predicted_flux'],
    )
    _scatter_with_fit(
        np.asarray([run['signed_flux'] for run in c_runs], dtype=float),
        np.asarray([run['predicted_signed_flux_pathmean'] for run in c_runs], dtype=float),
        'state signed flux',
        'predicted signed flux',
        'Benchmark C: predicted signed flux vs state signed flux',
        plot_paths['predicted_flux_vs_state_flux'],
    )
    patch = payloads['benchmark_c']['patchwise_explanation']['center_summaries']
    _scatter_with_fit(
        np.asarray([row['mean_response_vs_state_flux_slope'] for row in patch], dtype=float),
        np.asarray([row['reconstructed_response_vs_state_flux_slope'] for row in patch], dtype=float),
        'observed response-vs-state-flux slope',
        'reconstructed slope',
        'Benchmark C: patchwise slope reconstruction',
        plot_paths['patchwise_reconstruction'],
    )

    _write_report(payloads, plot_paths, args.report_root / 'CWT-CGT_Phase_6_Jacobian_Report.md')


if __name__ == '__main__':
    main()
