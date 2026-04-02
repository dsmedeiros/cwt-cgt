from __future__ import annotations

import copy
import json
import math
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


@dataclass(frozen=True)
class Phase25Config:
    benchmark_focus: str = 'benchmark_c'
    default_switch_gamma: float = 0.30
    source_phase24_filename: str = 'benchmark_c_phase24_clean_rerun_higher_order.json'


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


def derive_moment_derived_higher_order_coefficients(train_rows: list[dict], baseline_coefficients: dict[str, float | None]) -> dict:
    trusted = [row for row in train_rows if row.get('trusted_pair')]
    if not trusted:
        return {
            'coefficients': {'m2_gap_var': None, 'm2_gap_boundary_var': None},
            'moments': {},
            'derivation': {},
        }
    means = {
        'mean_abs_m2_gap': float(np.mean(np.abs([float(row['m2_gap']) for row in trusted]))),
        'mean_abs_m2_gap_boundary': float(np.mean(np.abs([float(row['m2_gap_boundary']) for row in trusted]))),
        'mean_abs_area_magnitude': float(np.mean(np.abs([float(row['area_magnitude']) for row in trusted]))),
        'mean_abs_m2_gap_var': float(np.mean(np.abs([float(row['m2_gap_var']) for row in trusted]))),
        'mean_abs_m2_gap_boundary_var': float(np.mean(np.abs([float(row['m2_gap_boundary_var']) for row in trusted]))),
    }
    eps = 1e-15
    coeff_gap_var = -abs(float(baseline_coefficients['m2_gap'])) * means['mean_abs_m2_gap'] / max(means['mean_abs_m2_gap_var'], eps)
    coeff_gap_boundary_var = math.sqrt(
        abs(float(baseline_coefficients['m2_gap_boundary']))
        * means['mean_abs_m2_gap_boundary']
        * abs(float(baseline_coefficients['area_magnitude']))
        * means['mean_abs_area_magnitude']
    ) / max(means['mean_abs_m2_gap_boundary_var'], eps)
    return {
        'coefficients': {
            'm2_gap_var': float(coeff_gap_var),
            'm2_gap_boundary_var': float(coeff_gap_boundary_var),
        },
        'moments': means,
        'derivation': {
            'm2_gap_var': '-|c_gap^(baseline)| * mean_abs(m2_gap) / mean_abs(m2_gap_var)',
            'm2_gap_boundary_var': '+sqrt(|c_boundary^(baseline)| mean_abs(m2_gap_boundary) * |c_area^(baseline)| mean_abs(area)) / mean_abs(m2_gap_boundary_var)',
        },
    }


def _augment_rows(rows: list[dict], baseline_coeffs: dict[str, float | None], derived_coeffs: dict[str, float | None]) -> list[dict]:
    out: list[dict] = []
    for row in rows:
        entry = dict(row)
        if row.get('trusted_pair'):
            pred = (
                float(baseline_coeffs['m2_gap']) * float(row['m2_gap'])
                + float(baseline_coeffs['m2_gap_boundary']) * float(row['m2_gap_boundary'])
                + float(baseline_coeffs['area_magnitude']) * float(row['area_magnitude'])
                + float(derived_coeffs['m2_gap_var']) * float(row['m2_gap_var'])
                + float(derived_coeffs['m2_gap_boundary_var']) * float(row['m2_gap_boundary_var'])
                + float(baseline_coeffs['intercept'])
            )
            entry['moment_derived_predictor'] = float(pred)
        else:
            entry['moment_derived_predictor'] = None
        out.append(entry)
    return out


def _plot_switch_scatter(path: Path, train_rows: list[dict], held_base_rows: list[dict], held_new_rows: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    groups = [('train', train_rows, 'o'), ('held-out base', held_base_rows, 's'), ('held-out new', held_new_rows, '^')]
    for label, rows, marker in groups:
        trusted = [row for row in rows if row.get('moment_derived_predictor') is not None]
        if not trusted:
            continue
        ax.scatter([float(row['moment_derived_predictor']) for row in trusted], [float(row['orientation_gap']) for row in trusted], label=label, marker=marker, alpha=0.85)
    ax.set_title('Benchmark C: observed vs moment-derived higher-order predictor @ switch γ')
    ax.set_xlabel('Moment-derived predictor')
    ax.set_ylabel('Observed orientation gap')
    ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_r2_lines(path: Path, gammas: list[float], baseline_new: list[float], fitted_new: list[float], moment_new: list[float], baseline_combined: list[float], fitted_combined: list[float], moment_combined: list[float]) -> None:
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    ax.plot(gammas, baseline_combined, marker='o', label='baseline held-out combined')
    ax.plot(gammas, fitted_combined, marker='s', label='phase24 higher-order combined')
    ax.plot(gammas, moment_combined, marker='^', label='moment-derived combined')
    ax.plot(gammas, baseline_new, marker='o', linestyle='--', label='baseline held-out new')
    ax.plot(gammas, fitted_new, marker='s', linestyle='--', label='phase24 higher-order new')
    ax.plot(gammas, moment_new, marker='^', linestyle='--', label='moment-derived new')
    ax.set_title('Benchmark C: held-out noisy-loop transfer vs dephasing')
    ax.set_xlabel('Dephasing γ')
    ax.set_ylabel('R²')
    ax.legend(loc='best', ncol=2)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_coefficients(path: Path, gammas: list[float], moment_coeffs: dict[str, list[float]], fitted_coeffs: dict[str, list[float]]) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.plot(gammas, moment_coeffs['m2_gap_var'], marker='o', label='moment-derived m2_gap_var')
    ax.plot(gammas, fitted_coeffs['m2_gap_var'], marker='o', linestyle='--', label='phase24 fitted m2_gap_var')
    ax.plot(gammas, moment_coeffs['m2_gap_boundary_var'], marker='s', label='moment-derived m2_gap_boundary_var')
    ax.plot(gammas, fitted_coeffs['m2_gap_boundary_var'], marker='s', linestyle='--', label='phase24 fitted m2_gap_boundary_var')
    ax.set_title('Benchmark C: higher-order coefficients vs dephasing')
    ax.set_xlabel('Dephasing γ')
    ax.set_ylabel('Coefficient value')
    ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def phase25_payload(project_root: Path, config: Phase25Config | None = None) -> dict:
    cfg = config or Phase25Config()
    project_root = Path(project_root)
    bench_dir = project_root / 'cgt_benchmarks' / 'results' / 'benchmark_C_ring'
    source_path = bench_dir / cfg.source_phase24_filename
    if not source_path.exists():
        raise FileNotFoundError(f'Missing Phase 24 source artifact: {source_path}')
    phase24 = json.loads(source_path.read_text())

    levels_out: list[dict] = []
    gammas: list[float] = []
    baseline_new_track: list[float] = []
    fitted_new_track: list[float] = []
    moment_new_track: list[float] = []
    baseline_combined_track: list[float] = []
    fitted_combined_track: list[float] = []
    moment_combined_track: list[float] = []
    moment_coeff_tracks = {'m2_gap_var': [], 'm2_gap_boundary_var': []}
    fitted_coeff_tracks = {'m2_gap_var': [], 'm2_gap_boundary_var': []}

    for source_level in phase24['levels']:
        gamma = float(source_level['dephasing'])
        rows = [copy.deepcopy(row) for row in source_level['rows']]
        train_rows = [row for row in rows if row.get('family_group') == 'train' and row.get('trusted_pair')]
        baseline_coeffs = dict(source_level['baseline_model']['coefficients'])
        derived = derive_moment_derived_higher_order_coefficients(train_rows, baseline_coeffs)
        augmented = _augment_rows(rows, baseline_coeffs, derived['coefficients'])

        train_aug = [row for row in augmented if row.get('family_group') == 'train']
        held_base_aug = [row for row in augmented if row.get('family_group') == 'heldout_base']
        held_new_aug = [row for row in augmented if row.get('family_group') == 'heldout_new']
        held_combined_aug = [row for row in augmented if row.get('family_group') != 'train']

        level_out = {
            'dephasing': gamma,
            'baseline_model': source_level['baseline_model'],
            'source_phase24_higher_order_model': source_level['higher_order_model'],
            'moment_derived_higher_order': {
                'coefficients': derived['coefficients'],
                'generator_moments': derived['moments'],
                'derivation': derived['derivation'],
                'train_fit': _prediction_summary(train_aug, 'moment_derived_predictor'),
                'heldout_base_fit': _prediction_summary(held_base_aug, 'moment_derived_predictor'),
                'heldout_new_fit': _prediction_summary(held_new_aug, 'moment_derived_predictor'),
                'heldout_combined_fit': _prediction_summary(held_combined_aug, 'moment_derived_predictor'),
            },
            'rows': augmented,
        }
        levels_out.append(level_out)
        gammas.append(gamma)
        baseline_new_track.append(float('nan') if source_level['baseline_model']['heldout_new_fit']['r2'] is None else float(source_level['baseline_model']['heldout_new_fit']['r2']))
        fitted_new_track.append(float('nan') if source_level['higher_order_model']['heldout_new_fit']['r2'] is None else float(source_level['higher_order_model']['heldout_new_fit']['r2']))
        moment_new_track.append(float('nan') if level_out['moment_derived_higher_order']['heldout_new_fit']['r2'] is None else float(level_out['moment_derived_higher_order']['heldout_new_fit']['r2']))
        baseline_combined_track.append(float('nan') if source_level['baseline_model']['heldout_combined_fit']['r2'] is None else float(source_level['baseline_model']['heldout_combined_fit']['r2']))
        fitted_combined_track.append(float('nan') if source_level['higher_order_model']['heldout_combined_fit']['r2'] is None else float(source_level['higher_order_model']['heldout_combined_fit']['r2']))
        moment_combined_track.append(float('nan') if level_out['moment_derived_higher_order']['heldout_combined_fit']['r2'] is None else float(level_out['moment_derived_higher_order']['heldout_combined_fit']['r2']))
        moment_coeff_tracks['m2_gap_var'].append(float(level_out['moment_derived_higher_order']['coefficients']['m2_gap_var']))
        moment_coeff_tracks['m2_gap_boundary_var'].append(float(level_out['moment_derived_higher_order']['coefficients']['m2_gap_boundary_var']))
        fitted_coeff_tracks['m2_gap_var'].append(float(source_level['higher_order_model']['coefficients']['m2_gap_var']))
        fitted_coeff_tracks['m2_gap_boundary_var'].append(float(source_level['higher_order_model']['coefficients']['m2_gap_boundary_var']))

    switch_level = min(levels_out, key=lambda row: abs(float(row['dephasing']) - cfg.default_switch_gamma))
    base_new = switch_level['baseline_model']['heldout_new_fit']['r2']
    base_comb = switch_level['baseline_model']['heldout_combined_fit']['r2']
    moment_new = switch_level['moment_derived_higher_order']['heldout_new_fit']['r2']
    moment_comb = switch_level['moment_derived_higher_order']['heldout_combined_fit']['r2']
    fitted_new = switch_level['source_phase24_higher_order_model']['heldout_new_fit']['r2']
    fitted_comb = switch_level['source_phase24_higher_order_model']['heldout_combined_fit']['r2']

    verdict = 'moment_derived_higher_order_uncertain'
    if all(val is not None for val in (base_new, base_comb, moment_new, moment_comb)):
        if float(moment_new) >= float(base_new) + 0.04 and float(moment_comb) >= float(base_comb) + 0.02:
            verdict = 'moment_derived_higher_order_supported'
        elif float(moment_new) >= float(base_new) + 0.04:
            verdict = 'moment_derived_new_family_improved'
        elif float(moment_comb) >= float(base_comb) + 0.02:
            verdict = 'moment_derived_combined_improved'
        else:
            verdict = 'moment_derived_higher_order_weak'

    payload = {
        'phase': 'phase25_moment_derived_higher_order_transfer',
        'benchmark': cfg.benchmark_focus,
        'slug': 'benchmark_C_ring',
        'description': phase24.get('description', 'Three-node ring first positive signed-loop benchmark.'),
        'source_phase24_artifact': str(source_path.relative_to(project_root)),
        'train_shapes': list(phase24.get('train_shapes', [])),
        'heldout_base_shapes': list(phase24.get('heldout_base_shapes', [])),
        'heldout_new_shapes': list(phase24.get('heldout_new_shapes', [])),
        'dephasing_values': gammas,
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
            'Phase 25 keeps the clean Phase 24 loop set and source rows fixed.',
            'The lower-order scaffold remains the accepted Phase 24 baseline model on (m2_gap, m2_gap_boundary, area).',
            'Only the higher-order coefficients are replaced, using generator-moment rules built from canonical train-row moments instead of response regression.',
            'This makes the higher-order correction more derived, but it does not yet remove the lower-order response-fitted scaffold.',
        ],
        'verdict': verdict,
        'switch_metrics': {
            'baseline_heldout_new_r2': base_new,
            'baseline_heldout_combined_r2': base_comb,
            'phase24_fitted_heldout_new_r2': fitted_new,
            'phase24_fitted_heldout_combined_r2': fitted_comb,
            'moment_derived_heldout_new_r2': moment_new,
            'moment_derived_heldout_combined_r2': moment_comb,
            'moment_derived_heldout_combined_corr': switch_level['moment_derived_higher_order']['heldout_combined_fit']['corr'],
            'moment_derived_heldout_combined_sign_agreement': switch_level['moment_derived_higher_order']['heldout_combined_fit']['sign_agreement'],
        },
    }

    out_path = bench_dir / 'benchmark_c_phase25_moment_derived_higher_order.json'
    out_path.write_text(json.dumps(payload, indent=2))

    plots_dir = project_root / 'cgt_benchmarks' / 'reports' / 'plots' / 'phase25_moment_derived' / 'benchmark_C_ring'
    train_rows = [row for row in switch_level['rows'] if row.get('family_group') == 'train']
    held_base_rows = [row for row in switch_level['rows'] if row.get('family_group') == 'heldout_base']
    held_new_rows = [row for row in switch_level['rows'] if row.get('family_group') == 'heldout_new']
    _plot_switch_scatter(plots_dir / 'response_vs_moment_derived_predictor_switch.png', train_rows, held_base_rows, held_new_rows)
    _plot_r2_lines(plots_dir / 'heldout_r2_vs_dephasing.png', gammas, baseline_new_track, fitted_new_track, moment_new_track, baseline_combined_track, fitted_combined_track, moment_combined_track)
    _plot_coefficients(plots_dir / 'higher_order_coefficients_vs_dephasing.png', gammas, moment_coeff_tracks, fitted_coeff_tracks)

    summary_path = project_root / 'cgt_benchmarks' / 'reports' / 'phase25_summary.json'
    summary_path.write_text(json.dumps(payload, indent=2))
    return payload
