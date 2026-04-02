from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


@dataclass(frozen=True)
class Phase22Config:
    benchmark_focus: str = 'benchmark_c'
    default_switch_gamma: float = 0.30
    source_phase21_filename: str = 'benchmark_c_phase21_heldout_shape_transfer.json'


def _prediction_summary(rows: list[dict], key: str) -> dict:
    trusted = [row for row in rows if row.get('trusted_pair') and row.get(key) is not None]
    if not trusted:
        return {'r2': None, 'corr': None, 'count': 0, 'sign_agreement': None}
    y = np.asarray([float(row['orientation_gap']) for row in trusted], dtype=float)
    yhat = np.asarray([float(row[key]) for row in trusted], dtype=float)
    ss = float(np.dot(y - float(np.mean(y)), y - float(np.mean(y))))
    r2 = None if ss <= 1e-15 else float(1.0 - np.dot(y - yhat, y - yhat) / ss)
    corr = None
    if len(y) >= 2 and not (np.allclose(yhat, yhat[0]) or np.allclose(y, y[0])):
        corr = float(np.corrcoef(y, yhat)[0, 1])
    sign_agreement = float(np.mean(np.sign(yhat) == np.sign(y))) if len(y) else None
    return {'r2': r2, 'corr': corr, 'count': int(len(y)), 'sign_agreement': sign_agreement}


def derive_generator_moment_coefficients(rows: list[dict]) -> dict:
    trusted = [row for row in rows if row.get('trusted_pair')]
    if not trusted:
        return {
            'coefficients': {'path_gap': None, 'path_gap_boundary_distance': None, 'area_magnitude': None, 'intercept': None},
            'moments': {'mean_abs_boundary_distance': None, 'mean_abs_path_gap': None, 'mean_abs_path_gap_boundary_distance': None, 'mean_abs_area': None},
        }
    boundary = np.asarray([abs(float(row['boundary_distance_u'])) for row in trusted], dtype=float)
    path_gap = np.asarray([abs(float(row['path_gap'])) for row in trusted], dtype=float)
    path_gap_boundary = np.asarray([abs(float(row['path_gap_boundary_distance'])) for row in trusted], dtype=float)
    area = np.asarray([abs(float(row['area_magnitude'])) for row in trusted], dtype=float)

    mean_abs_boundary = float(np.mean(boundary))
    mean_abs_path_gap = float(np.mean(path_gap))
    mean_abs_path_gap_boundary = float(np.mean(path_gap_boundary))
    mean_abs_area = float(np.mean(area))

    coeff_path = 0.5 * mean_abs_boundary
    coeff_boundary = -coeff_path * mean_abs_path_gap / max(mean_abs_path_gap_boundary, 1e-15)
    coeff_area = -float(np.sqrt(mean_abs_path_gap * mean_abs_path_gap_boundary)) / max(mean_abs_area, 1e-15)

    return {
        'coefficients': {
            'path_gap': float(coeff_path),
            'path_gap_boundary_distance': float(coeff_boundary),
            'area_magnitude': float(coeff_area),
            'intercept': 0.0,
        },
        'moments': {
            'mean_abs_boundary_distance': mean_abs_boundary,
            'mean_abs_path_gap': mean_abs_path_gap,
            'mean_abs_path_gap_boundary_distance': mean_abs_path_gap_boundary,
            'mean_abs_area': mean_abs_area,
        },
        'derivation': {
            'path_gap': '0.5 * mean_abs_boundary_distance',
            'path_gap_boundary_distance': '-path_gap_coeff * mean_abs_path_gap / mean_abs_path_gap_boundary_distance',
            'area_magnitude': '-sqrt(mean_abs_path_gap * mean_abs_path_gap_boundary_distance) / mean_abs_area',
            'intercept': '0.0',
        },
    }


def _plot_switch_scatter(path: Path, train_rows: list[dict], held_rows: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(6.6, 4.4))
    if train_rows:
        ax.scatter(
            [float(row['generator_moment_predictor']) for row in train_rows],
            [float(row['orientation_gap']) for row in train_rows],
            label='train',
            alpha=0.85,
        )
    if held_rows:
        ax.scatter(
            [float(row['generator_moment_predictor']) for row in held_rows],
            [float(row['orientation_gap']) for row in held_rows],
            label='held-out',
            alpha=0.85,
        )
    ax.set_title('Benchmark C: observed vs generator-moment predictor at switch γ')
    ax.set_xlabel('Generator-moment predictor')
    ax.set_ylabel('Observed orientation gap')
    if train_rows or held_rows:
        ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_r2_lines(path: Path, gammas: list[float], train_r2: list[float], held_r2: list[float]) -> None:
    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    ax.plot(gammas, train_r2, marker='o', label='train')
    ax.plot(gammas, held_r2, marker='s', label='held-out')
    ax.set_title('Benchmark C: generator-moment train vs held-out R²')
    ax.set_xlabel('Dephasing γ')
    ax.set_ylabel('R²')
    ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_coefficients(path: Path, gammas: list[float], coeffs_by_gamma: dict[str, list[float]]) -> None:
    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    ax.plot(gammas, coeffs_by_gamma['path_gap'], marker='o', label='path_gap')
    ax.plot(gammas, coeffs_by_gamma['path_gap_boundary_distance'], marker='s', label='path_gap_boundary_distance')
    ax.plot(gammas, coeffs_by_gamma['area_magnitude'], marker='^', label='area_magnitude')
    ax.set_title('Benchmark C: generator-moment coefficients vs dephasing')
    ax.set_xlabel('Dephasing γ')
    ax.set_ylabel('Coefficient value')
    ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def phase22_payload(project_root: Path, config: Phase22Config | None = None) -> dict:
    cfg = config or Phase22Config()
    project_root = Path(project_root)
    results_root = project_root / 'cgt_benchmarks' / 'results'
    bench_dir = results_root / 'benchmark_C_ring'
    source_path = bench_dir / cfg.source_phase21_filename
    if not source_path.exists():
        raise FileNotFoundError(f'Missing Phase 21 source artifact: {source_path}')
    phase21 = json.loads(source_path.read_text())

    levels_out: list[dict] = []
    coeff_tracks = {'path_gap': [], 'path_gap_boundary_distance': [], 'area_magnitude': []}
    gamma_values: list[float] = []

    for level in phase21['levels']:
        gamma = float(level['dephasing'])
        rows = [dict(row) for row in level['annotated_rows'] if row.get('trusted_pair')]
        train_rows = [row for row in rows if row.get('family_group') == 'train']
        held_rows = [row for row in rows if row.get('family_group') == 'heldout']
        derived = derive_generator_moment_coefficients(train_rows)
        coeffs = derived['coefficients']
        for row in rows:
            row['generator_moment_predictor'] = (
                coeffs['path_gap'] * float(row['path_gap'])
                + coeffs['path_gap_boundary_distance'] * float(row['path_gap_boundary_distance'])
                + coeffs['area_magnitude'] * float(row['area_magnitude'])
                + coeffs['intercept']
            )
        train_rows = [row for row in rows if row.get('family_group') == 'train']
        held_rows = [row for row in rows if row.get('family_group') == 'heldout']
        switch_coeffs = level.get('coefficients', {})
        level_out = {
            'dephasing': gamma,
            'generator_moment_coefficients': coeffs,
            'generator_moment_inputs': derived['moments'],
            'generator_moment_derivation': derived['derivation'],
            'phase21_fitted_coefficients': switch_coeffs,
            'coefficient_deltas_vs_phase21_fit': {
                key: None if switch_coeffs.get(key) is None else float(coeffs[key] - float(switch_coeffs[key]))
                for key in ('path_gap', 'path_gap_boundary_distance', 'area_magnitude')
            },
            'train_fit': _prediction_summary(train_rows, 'generator_moment_predictor'),
            'heldout_fit': _prediction_summary(held_rows, 'generator_moment_predictor'),
            'all_fit': _prediction_summary(rows, 'generator_moment_predictor'),
            'shape_counts': {'train': int(len(train_rows)), 'heldout': int(len(held_rows))},
            'rows': rows,
        }
        levels_out.append(level_out)
        gamma_values.append(gamma)
        coeff_tracks['path_gap'].append(float(coeffs['path_gap']))
        coeff_tracks['path_gap_boundary_distance'].append(float(coeffs['path_gap_boundary_distance']))
        coeff_tracks['area_magnitude'].append(float(coeffs['area_magnitude']))

    switch_level = min(levels_out, key=lambda row: abs(float(row['dephasing']) - cfg.default_switch_gamma))
    verdict = 'generator_moment_transfer_partial'
    heldout_r2 = switch_level['heldout_fit']['r2']
    if heldout_r2 is not None and float(heldout_r2) >= 0.90:
        verdict = 'generator_moment_transfer_supported'
    elif heldout_r2 is not None and float(heldout_r2) < 0.50:
        verdict = 'generator_moment_transfer_weak'

    payload = {
        'phase': 'phase22_generator_moment_coefficients',
        'benchmark': cfg.benchmark_focus,
        'slug': 'benchmark_C_ring',
        'description': phase21.get('description', 'Three-node ring first positive signed-loop benchmark.'),
        'source_phase21_artifact': str(source_path.relative_to(project_root)),
        'train_shapes': list(phase21.get('train_shapes', [])),
        'heldout_shapes': list(phase21.get('heldout_shapes', [])),
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
            'Phase 22 removes direct response fitting from the held-out transfer coefficients.',
            'The three loop-side coefficients are derived from local generator moments measured on canonical train rows only.',
            'Held-out evaluation remains unchanged: diamond and rounded_square are scored with no coefficient refit.',
        ],
        'verdict': verdict,
    }

    out_path = bench_dir / 'benchmark_c_phase22_generator_moment_transfer.json'
    out_path.write_text(json.dumps(payload, indent=2))

    plots_dir = project_root / 'cgt_benchmarks' / 'reports' / 'plots' / 'phase22_generator_moments' / 'benchmark_C_ring'
    train_rows = [row for row in switch_level['rows'] if row.get('family_group') == 'train']
    held_rows = [row for row in switch_level['rows'] if row.get('family_group') == 'heldout']
    _plot_switch_scatter(plots_dir / 'response_vs_generator_moment_predictor_switch.png', train_rows, held_rows)
    _plot_r2_lines(
        plots_dir / 'train_vs_heldout_r2.png',
        gamma_values,
        [float('nan') if level['train_fit']['r2'] is None else float(level['train_fit']['r2']) for level in levels_out],
        [float('nan') if level['heldout_fit']['r2'] is None else float(level['heldout_fit']['r2']) for level in levels_out],
    )
    _plot_coefficients(plots_dir / 'coefficients_vs_dephasing.png', gamma_values, coeff_tracks)

    summary_path = project_root / 'cgt_benchmarks' / 'reports' / 'phase22_summary.json'
    summary_path.write_text(json.dumps(payload, indent=2))
    return payload
