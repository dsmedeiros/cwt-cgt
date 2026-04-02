from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from ..benchmarks import get_benchmark
from ..lindblad import LindbladConfig
from .phase21_analysis import _load_phase18_zero_crossing, _prediction_summary, _run_loop_pair


@dataclass(frozen=True)
class Phase23Config:
    benchmark_focus: str = 'benchmark_c'
    source_phase22_filename: str = 'benchmark_c_phase22_generator_moment_transfer.json'
    new_heldout_shapes: tuple[str, ...] = ('ellipse', 'stadium')
    default_switch_gamma: float = 0.30
    focus_max_centers: int = 2
    focus_max_side_lengths: int = 3
    focus_steps_per_segment: int = 8


def _plot_switch_scatter(path: Path, train_rows: list[dict], base_rows: list[dict], new_rows: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(6.8, 4.4))
    if train_rows:
        ax.scatter([float(r['generator_moment_predictor']) for r in train_rows], [float(r['orientation_gap']) for r in train_rows], label='train', alpha=0.85)
    if base_rows:
        ax.scatter([float(r['generator_moment_predictor']) for r in base_rows], [float(r['orientation_gap']) for r in base_rows], label='held-out base', alpha=0.85)
    if new_rows:
        ax.scatter([float(r['generator_moment_predictor']) for r in new_rows], [float(r['orientation_gap']) for r in new_rows], label='held-out new', alpha=0.85)
    ax.set_title('Benchmark C: broader held-out transfer at switch γ')
    ax.set_xlabel('Generator-moment predictor')
    ax.set_ylabel('Observed orientation gap')
    if train_rows or base_rows or new_rows:
        ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_r2_lines(path: Path, gammas: list[float], train_r2: list[float], base_r2: list[float], new_r2: list[float], combined_r2: list[float]) -> None:
    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    ax.plot(gammas, train_r2, marker='o', label='train')
    ax.plot(gammas, base_r2, marker='s', label='held-out base')
    ax.plot(gammas, new_r2, marker='^', label='held-out new')
    ax.plot(gammas, combined_r2, marker='d', label='held-out combined')
    ax.set_title('Benchmark C: broader held-out family transfer')
    ax.set_xlabel('Dephasing γ')
    ax.set_ylabel('R²')
    ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_per_shape(path: Path, shape_summaries: dict[str, dict]) -> None:
    names = list(shape_summaries)
    vals = [np.nan if shape_summaries[name]['r2'] is None else float(shape_summaries[name]['r2']) for name in names]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.bar(names, vals)
    ax.set_title('Benchmark C: per-shape held-out R² at switch γ')
    ax.set_ylabel('R²')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def phase23_payload(project_root: Path, config: Phase23Config | None = None, lindblad_config: LindbladConfig | None = None) -> dict:
    cfg = config or Phase23Config()
    project_root = Path(project_root)
    results_root = project_root / 'cgt_benchmarks' / 'results'
    benchmark = get_benchmark(cfg.benchmark_focus)
    bench_dir = results_root / benchmark.slug
    source_path = bench_dir / cfg.source_phase22_filename
    if not source_path.exists():
        raise FileNotFoundError(f'Missing Phase 22 source artifact: {source_path}')
    phase22 = json.loads(source_path.read_text())
    lind_cfg = lindblad_config or LindbladConfig(dephasing_values=tuple(float(x) for x in phase22.get('dephasing_values', (0.0, 0.10, 0.20, 0.30))))

    zero_u = _load_phase18_zero_crossing(results_root, cfg.benchmark_focus)
    centers = benchmark.default_loop_centers[: cfg.focus_max_centers]
    side_lengths = benchmark.default_loop_side_lengths[: cfg.focus_max_side_lengths]

    levels_out: list[dict] = []
    gamma_values: list[float] = []
    train_r2: list[float] = []
    base_r2: list[float] = []
    new_r2: list[float] = []
    combined_r2: list[float] = []

    for source_level in phase22['levels']:
        gamma = float(source_level['dephasing'])
        coeffs = source_level['generator_moment_coefficients']

        source_rows = [dict(row) for row in source_level['rows'] if row.get('trusted_pair')]
        for row in source_rows:
            row['generator_moment_predictor'] = float(row.get('generator_moment_predictor'))
            row['provenance'] = 'phase22_source'
            if row['shape'] in phase22.get('train_shapes', []):
                row['family_group'] = 'train'
            else:
                row['family_group'] = 'heldout_base'

        generated_rows: list[dict] = []
        for shape in cfg.new_heldout_shapes:
            for center in centers:
                for side in side_lengths:
                    row = _run_loop_pair(cfg.benchmark_focus, shape, center, float(side), gamma, cfg.focus_steps_per_segment, lind_cfg)
                    row['provenance'] = 'phase23_generated'
                    row['family_group'] = 'heldout_new'
                    if row.get('trusted_pair'):
                        dist = 0.0 if zero_u is None else float(center[0] - zero_u)
                        row['boundary_distance_u'] = None if zero_u is None else dist
                        row['path_gap_boundary_distance'] = float(row['path_gap'] * dist)
                        row['generator_moment_predictor'] = float(
                            coeffs['path_gap'] * float(row['path_gap'])
                            + coeffs['path_gap_boundary_distance'] * float(row['path_gap_boundary_distance'])
                            + coeffs['area_magnitude'] * float(row['area_magnitude'])
                            + coeffs['intercept']
                        )
                    else:
                        row['boundary_distance_u'] = None if zero_u is None else float(center[0] - zero_u)
                        row['path_gap_boundary_distance'] = None
                        row['generator_moment_predictor'] = None
                    generated_rows.append(row)

        train_rows = [row for row in source_rows if row['family_group'] == 'train']
        base_rows = [row for row in source_rows if row['family_group'] == 'heldout_base']
        new_rows = [row for row in generated_rows if row.get('trusted_pair')]
        all_held_rows = base_rows + new_rows
        all_rows = train_rows + all_held_rows

        shape_summaries = {}
        for shape in tuple(phase22.get('heldout_shapes', [])) + cfg.new_heldout_shapes:
            subset = [row for row in all_held_rows if row['shape'] == shape]
            shape_summaries[shape] = _prediction_summary(subset, 'generator_moment_predictor')

        level_out = {
            'dephasing': gamma,
            'generator_moment_coefficients': coeffs,
            'zero_crossing_u_mean': zero_u,
            'train_fit': _prediction_summary(train_rows, 'generator_moment_predictor'),
            'heldout_base_fit': _prediction_summary(base_rows, 'generator_moment_predictor'),
            'heldout_new_fit': _prediction_summary(new_rows, 'generator_moment_predictor'),
            'heldout_combined_fit': _prediction_summary(all_held_rows, 'generator_moment_predictor'),
            'all_fit': _prediction_summary(all_rows, 'generator_moment_predictor'),
            'shape_counts': {
                'train': int(len(train_rows)),
                'heldout_base': int(len(base_rows)),
                'heldout_new': int(len(new_rows)),
            },
            'per_shape_fit': shape_summaries,
            'source_rows': source_rows,
            'generated_rows': generated_rows,
        }
        levels_out.append(level_out)
        gamma_values.append(gamma)
        train_r2.append(np.nan if level_out['train_fit']['r2'] is None else float(level_out['train_fit']['r2']))
        base_r2.append(np.nan if level_out['heldout_base_fit']['r2'] is None else float(level_out['heldout_base_fit']['r2']))
        new_r2.append(np.nan if level_out['heldout_new_fit']['r2'] is None else float(level_out['heldout_new_fit']['r2']))
        combined_r2.append(np.nan if level_out['heldout_combined_fit']['r2'] is None else float(level_out['heldout_combined_fit']['r2']))

    switch_level = min(levels_out, key=lambda row: abs(float(row['dephasing']) - cfg.default_switch_gamma))
    combined_switch_r2 = switch_level['heldout_combined_fit']['r2']
    new_switch_r2 = switch_level['heldout_new_fit']['r2']
    verdict = 'broader_generator_transfer_weak'
    if combined_switch_r2 is not None and new_switch_r2 is not None:
        if float(combined_switch_r2) >= 0.85 and float(new_switch_r2) >= 0.75:
            verdict = 'broader_generator_generalization_with_decay'
        elif float(combined_switch_r2) >= 0.65 and float(new_switch_r2) >= 0.50:
            verdict = 'broader_generator_generalization_partial'

    payload = {
        'phase': 'phase23_broader_heldout_generator_transfer',
        'benchmark': cfg.benchmark_focus,
        'slug': benchmark.slug,
        'description': benchmark.description,
        'source_phase22_artifact': str(source_path.relative_to(project_root)),
        'train_shapes': list(phase22.get('train_shapes', [])),
        'heldout_base_shapes': list(phase22.get('heldout_shapes', [])),
        'heldout_new_shapes': list(cfg.new_heldout_shapes),
        'dephasing_values': gamma_values,
        'switch_gamma': float(switch_level['dephasing']),
        'switch_level': switch_level,
        'levels': levels_out,
        'suite_verdicts': {
            'benchmark_a': 'null_like (inherited)',
            'benchmark_b': 'weak_control (inherited)',
            'benchmark_c': verdict,
            'benchmark_d': 'null_like (inherited)',
            'benchmark_f': 'excluded_R4 (inherited)',
        },
        'notes': [
            'Phase 23 broadens the held-out family set beyond diamond and rounded_square by adding ellipse and stadium loops.',
            'The generator-moment coefficients are reused from the accepted Phase 22 artifact with no response refit.',
            'Base held-out rows remain anchored to the accepted Phase 22 source artifact; new-family rows are generated in this phase and scored under the same coefficients.',
        ],
        'verdict': verdict,
    }

    out_path = bench_dir / 'benchmark_c_phase23_broader_heldout_transfer.json'
    out_path.write_text(json.dumps(payload, indent=2))

    plots_dir = project_root / 'cgt_benchmarks' / 'reports' / 'plots' / 'phase23_broader_heldout' / benchmark.slug
    train_rows = switch_level['source_rows']
    train_rows = [row for row in train_rows if row['family_group'] == 'train']
    base_rows = [row for row in switch_level['source_rows'] if row['family_group'] == 'heldout_base']
    new_rows = [row for row in switch_level['generated_rows'] if row.get('trusted_pair')]
    _plot_switch_scatter(plots_dir / 'response_vs_generator_moment_predictor_switch.png', train_rows, base_rows, new_rows)
    _plot_r2_lines(plots_dir / 'train_vs_broader_heldout_r2.png', gamma_values, train_r2, base_r2, new_r2, combined_r2)
    _plot_per_shape(plots_dir / 'per_shape_r2_switch.png', switch_level['per_shape_fit'])

    summary_path = project_root / 'cgt_benchmarks' / 'reports' / 'phase23_summary.json'
    summary_path.write_text(json.dumps(payload, indent=2))
    return payload
