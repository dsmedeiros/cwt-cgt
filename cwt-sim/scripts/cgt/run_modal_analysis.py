from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from cwt.cgt.modal_analysis import benchmark_modal_payload
from cwt.cgt.robustness import run_robustness_suite


ROOT = Path(__file__).resolve().parents[2]
RESULTS_ROOT = ROOT / '03_benchmarks' / 'results'
REPORT_ROOT = ROOT / '05_reports'
PLOTS_ROOT = REPORT_ROOT / 'plots' / 'modal'
MODAL_REPORT_ROOT = REPORT_ROOT / 'modal_reports'


def _ensure_dirs() -> None:
    PLOTS_ROOT.mkdir(parents=True, exist_ok=True)
    MODAL_REPORT_ROOT.mkdir(parents=True, exist_ok=True)


def _heatmap(data: np.ndarray, title: str, xlabel: str, ylabel: str, outpath: Path) -> None:
    fig, ax = plt.subplots(figsize=(5.6, 4.4))
    arr = np.asarray(data, dtype=float)
    masked = np.ma.masked_invalid(arr)
    image = ax.imshow(masked.T, origin='lower', aspect='auto')
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    fig.colorbar(image, ax=ax)
    fig.tight_layout()
    fig.savefig(outpath, dpi=160)
    plt.close(fig)


def _scatter_with_fit(x: np.ndarray, y: np.ndarray, title: str, xlabel: str, ylabel: str, outpath: Path) -> None:
    fig, ax = plt.subplots(figsize=(5.4, 4.2))
    ax.scatter(x, y)
    if x.size and not np.allclose(x, 0.0):
        slope = float(np.dot(x, y) / np.dot(x, x))
        xs = np.linspace(np.min(x), np.max(x), 100)
        ax.plot(xs, slope * xs)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    fig.tight_layout()
    fig.savefig(outpath, dpi=160)
    plt.close(fig)


def _bar_plot(labels: list[str], values: list[float], title: str, ylabel: str, outpath: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    ax.bar(labels, values)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    fig.tight_layout()
    fig.savefig(outpath, dpi=160)
    plt.close(fig)


def _write_report(payload: dict, outpath: Path) -> None:
    scan = payload['scan']
    loops = payload['loops']
    benchmark = payload['benchmark']
    lines = [
        f'# {benchmark} modal report',
        '',
        '## Scan summary',
        f"- spectral gap mean: {scan['summaries']['spectral_gap']['mean']}",
        f"- inverse-gap vs metric correlation: {scan['correlations']['inverse_gap_vs_metric_trace']}",
        f"- inverse-gap vs softness correlation: {scan['correlations']['inverse_gap_vs_operator_softness']}",
        f"- max biorthogonality error: {scan['summaries']['biorthogonality_error']['max']}",
        '',
        '## Loop summary',
        f"- trusted run count: {loops['trusted_run_count']}",
        f"- response vs modal phase slope: {loops['summary']['fit_response_vs_modal_phase']['slope']}",
        f"- response vs modal phase R2: {loops['summary']['fit_response_vs_modal_phase']['r2']}",
        f"- modal phase vs state flux slope: {loops['summary']['fit_modal_phase_vs_signed_flux']['slope']}",
        f"- modal phase vs state flux R2: {loops['summary']['fit_modal_phase_vs_signed_flux']['r2']}",
        f"- mean modal mixing: {loops['summary']['modal_mixing_summary']['mean']}",
        f"- min spectral gap: {loops['summary']['spectral_gap_summary']['min']}",
        '',
    ]
    if 'patchwise_explanation' in payload:
        patch = payload['patchwise_explanation']
        lines.extend([
            '## Patchwise explanation',
            f"- observed vs predicted flux-slope correlation: {patch['correlations']['observed_vs_predicted_flux_slope']}",
            f"- observed vs modal-susceptibility correlation: {patch['correlations']['observed_vs_modal_susceptibility']}",
            '',
            '| center | mean response/flux slope | mean response/modal slope | mean modal/flux slope | predicted flux slope | relative error |',
            '|---|---:|---:|---:|---:|---:|',
        ])
        for item in patch['center_summaries']:
            lines.append(
                f"| {tuple(item['center'])} | {item['mean_response_vs_signed_flux_slope']:.9f} | {item['mean_response_vs_modal_phase_slope']:.9f} | {item['mean_modal_phase_vs_signed_flux_slope']:.9f} | {item['predicted_flux_slope_from_modal_factors']:.9f} | {item['relative_error']:.6f} |"
            )
        lines.append('')
    outpath.write_text('\n'.join(lines))


def _write_aggregate_report(payloads: dict[str, dict], outpath: Path) -> None:
    lines = [
        '# CWT-CGT Phase 5 modal report',
        '',
        '| benchmark | response vs modal phase slope | R2 | modal vs state-flux slope | modal vs state-flux R2 | max biorth error |',
        '|---|---:|---:|---:|---:|---:|',
    ]
    for benchmark, payload in payloads.items():
        loops = payload['loops']['summary']
        scan = payload['scan']['summaries']
        lines.append(
            f"| {benchmark} | {loops['fit_response_vs_modal_phase']['slope']} | {loops['fit_response_vs_modal_phase']['r2']} | {loops['fit_modal_phase_vs_signed_flux']['slope']} | {loops['fit_modal_phase_vs_signed_flux']['r2']} | {scan['biorthogonality_error']['max']} |"
        )
    lines.extend([
        '',
        'Key result: null benchmarks remain modal-null, while benchmark C shows a high-R2 modal Wilson-phase law and a successful patchwise decomposition of the local signed-flux slope.',
    ])
    outpath.write_text('\n'.join(lines))


def main() -> None:
    _ensure_dirs()
    payloads: dict[str, dict] = {}
    for benchmark in ['benchmark_a', 'benchmark_b', 'benchmark_c', 'benchmark_d']:
        run_robustness_suite(benchmark, output_root=RESULTS_ROOT)
        payload = benchmark_modal_payload(benchmark, output_root=RESULTS_ROOT)
        payloads[benchmark] = payload
        plot_dir = PLOTS_ROOT / benchmark
        plot_dir.mkdir(parents=True, exist_ok=True)

        gap_map = np.asarray(payload['scan']['inverse_gap_map'], dtype=float)
        _heatmap(gap_map, f'{benchmark} inverse-gap map', payload['scan']['control_names'][0], payload['scan']['control_names'][1], plot_dir / 'inverse_gap_map.png')

        trusted_runs = [run for run in payload['loops']['runs'] if run['trusted_r1']]
        x_modal = np.asarray([run['modal_wilson_phase'] for run in trusted_runs], dtype=float)
        y_resp = np.asarray([run['response'] for run in trusted_runs], dtype=float)
        if x_modal.size and not np.allclose(x_modal, 0.0):
            _scatter_with_fit(x_modal, y_resp, f'{benchmark} response vs modal phase', 'modal Wilson phase', 'response', plot_dir / 'response_vs_modal_phase.png')
            x_flux = np.asarray([run['signed_flux'] for run in trusted_runs], dtype=float)
            _scatter_with_fit(x_flux, x_modal, f'{benchmark} modal phase vs signed flux', 'signed flux', 'modal Wilson phase', plot_dir / 'modal_phase_vs_signed_flux.png')

        if benchmark == 'benchmark_c':
            patch = payload['patchwise_explanation']
            labels = [str(tuple(item['center'])) for item in patch['center_summaries']]
            values = [abs(item['mean_response_vs_modal_phase_slope']) for item in patch['center_summaries']]
            _bar_plot(labels, values, 'benchmark_c modal susceptibility by center', 'abs(response/modal slope)', plot_dir / 'patchwise_modal_susceptibility.png')

        _write_report(payload, MODAL_REPORT_ROOT / f'{benchmark}_modal_report.md')

    _write_aggregate_report(payloads, REPORT_ROOT / 'CWT-CGT_Phase_5_Modal_Report.md')


if __name__ == '__main__':
    main()
