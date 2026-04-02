from __future__ import annotations

import copy
import json
import math
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


@dataclass(frozen=True)
class Phase28Config:
    benchmark_focus: str = 'benchmark_c'
    default_switch_gamma: float = 0.30
    source_phase24_filename: str = 'benchmark_c_phase24_clean_rerun_higher_order.json'
    source_phase26_filename: str = 'benchmark_c_phase26_generator_normalized_transfer.json'
    source_phase27_filename: str = 'benchmark_c_phase27_moment_normalized_transfer.json'


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


def derive_generator_geometry_lower_order_coefficients(train_rows: list[dict]) -> dict:
    trusted = [row for row in train_rows if row.get('trusted_pair')]
    if not trusted:
        return {
            'coefficients': {'m2_gap': None, 'm2_gap_boundary': None, 'area_magnitude': None, 'intercept': None},
            'generator_moments': {},
            'compactness': {},
            'derivation': {},
        }

    abs_boundary = np.abs([float(row['boundary_distance_u']) for row in trusted])
    abs_gap = np.abs([float(row['m2_gap']) for row in trusted])
    abs_gap_boundary = np.abs([float(row['m2_gap_boundary']) for row in trusted])
    abs_area = np.abs([float(row['area_magnitude']) for row in trusted])

    mean_abs_boundary = float(np.mean(abs_boundary))
    mean_abs_gap = float(np.mean(abs_gap))
    mean_abs_gap_boundary = float(np.mean(abs_gap_boundary))
    mean_abs_area = float(np.mean(abs_area))

    rms_boundary = float(np.sqrt(np.mean(abs_boundary ** 2)))
    rms_gap = float(np.sqrt(np.mean(abs_gap ** 2)))
    rms_gap_boundary = float(np.sqrt(np.mean(abs_gap_boundary ** 2)))
    rms_area = float(np.sqrt(np.mean(abs_area ** 2)))

    mean_signed_gap = abs(float(np.mean([float(row['m2_gap']) for row in trusted])))
    polarization = mean_signed_gap / max(mean_abs_gap, 1e-15)
    boundary_ratio = mean_signed_gap / max(mean_abs_gap_boundary, 1e-15)

    boundary_compactness = mean_abs_boundary / max(rms_boundary, 1e-15)
    transport_compactness = mean_abs_gap / max(rms_gap, 1e-15)
    boundary_transport_compactness = mean_abs_gap_boundary / max(rms_gap_boundary, 1e-15)
    area_compactness = mean_abs_area / max(rms_area, 1e-15)

    alpha_gap = 1.0 - boundary_compactness ** 2
    beta_boundary = boundary_compactness * transport_compactness * boundary_transport_compactness
    gamma_area = 0.5 * (boundary_compactness + boundary_transport_compactness)

    coeff_gap = alpha_gap * mean_abs_boundary * (1.0 - polarization)
    coeff_gap_boundary = beta_boundary * mean_abs_boundary * (boundary_ratio ** 3)
    coeff_area = -gamma_area * math.sqrt(mean_abs_gap * mean_abs_gap_boundary) / max(mean_abs_area, 1e-15)

    return {
        'coefficients': {
            'm2_gap': float(coeff_gap),
            'm2_gap_boundary': float(coeff_gap_boundary),
            'area_magnitude': float(coeff_area),
            'intercept': 0.0,
        },
        'generator_moments': {
            'mean_abs_boundary_distance': mean_abs_boundary,
            'mean_abs_m2_gap': mean_abs_gap,
            'mean_abs_m2_gap_boundary': mean_abs_gap_boundary,
            'mean_abs_area_magnitude': mean_abs_area,
            'rms_boundary_distance': rms_boundary,
            'rms_m2_gap': rms_gap,
            'rms_m2_gap_boundary': rms_gap_boundary,
            'rms_area_magnitude': rms_area,
            'mean_signed_m2_gap': mean_signed_gap,
            'polarization': polarization,
            'boundary_ratio': boundary_ratio,
        },
        'compactness': {
            'boundary_compactness': boundary_compactness,
            'transport_compactness': transport_compactness,
            'boundary_transport_compactness': boundary_transport_compactness,
            'area_compactness': area_compactness,
            'alpha_gap': alpha_gap,
            'beta_boundary': beta_boundary,
            'gamma_area': gamma_area,
        },
        'derivation': {
            'boundary_compactness': 'mean_abs_boundary_distance / rms_boundary_distance',
            'transport_compactness': 'mean_abs(m2_gap) / rms(m2_gap)',
            'boundary_transport_compactness': 'mean_abs(m2_gap_boundary) / rms(m2_gap_boundary)',
            'area_compactness': 'mean_abs(area) / rms(area)',
            'alpha_gap': '1 - boundary_compactness^2',
            'beta_boundary': 'boundary_compactness * transport_compactness * boundary_transport_compactness',
            'gamma_area': '0.5 * (boundary_compactness + boundary_transport_compactness)',
            'm2_gap': 'alpha_gap * mean_abs_boundary_distance * (1 - polarization)',
            'm2_gap_boundary': 'beta_boundary * mean_abs_boundary_distance * boundary_ratio^3',
            'area_magnitude': '-gamma_area * sqrt(mean_abs(m2_gap) * mean_abs(m2_gap_boundary)) / mean_abs(area)',
            'intercept': '0.0',
        },
    }


def derive_higher_order_coefficients(train_rows: list[dict], lower_coefficients: dict[str, float | None]) -> dict:
    trusted = [row for row in train_rows if row.get('trusted_pair')]
    if not trusted:
        return {
            'coefficients': {'m2_gap_var': None, 'm2_gap_boundary_var': None},
            'generator_moments': {},
            'derivation': {},
        }

    mean_abs_gap = float(np.mean(np.abs([float(row['m2_gap']) for row in trusted])))
    mean_abs_gap_boundary = float(np.mean(np.abs([float(row['m2_gap_boundary']) for row in trusted])))
    mean_abs_area = float(np.mean(np.abs([float(row['area_magnitude']) for row in trusted])))
    mean_abs_gap_var = float(np.mean(np.abs([float(row['m2_gap_var']) for row in trusted])))
    mean_abs_gap_boundary_var = float(np.mean(np.abs([float(row['m2_gap_boundary_var']) for row in trusted])))

    coeff_gap_var = -abs(float(lower_coefficients['m2_gap'])) * mean_abs_gap / max(mean_abs_gap_var, 1e-15)
    coeff_gap_boundary_var = math.sqrt(
        abs(float(lower_coefficients['m2_gap_boundary'])) * mean_abs_gap_boundary * abs(float(lower_coefficients['area_magnitude'])) * mean_abs_area
    ) / max(mean_abs_gap_boundary_var, 1e-15)

    return {
        'coefficients': {
            'm2_gap_var': float(coeff_gap_var),
            'm2_gap_boundary_var': float(coeff_gap_boundary_var),
        },
        'generator_moments': {
            'mean_abs_m2_gap': mean_abs_gap,
            'mean_abs_m2_gap_boundary': mean_abs_gap_boundary,
            'mean_abs_area_magnitude': mean_abs_area,
            'mean_abs_m2_gap_var': mean_abs_gap_var,
            'mean_abs_m2_gap_boundary_var': mean_abs_gap_boundary_var,
        },
        'derivation': {
            'm2_gap_var': '-|c_gap^(generator-geometry)| * mean_abs(m2_gap) / mean_abs(m2_gap_var)',
            'm2_gap_boundary_var': '+sqrt(|c_boundary^(generator-geometry)| mean_abs(m2_gap_boundary) * |c_area^(generator-geometry)| mean_abs(area)) / mean_abs(m2_gap_boundary_var)',
        },
    }


def _augment_rows(rows: list[dict], lower_coeffs: dict[str, float | None], higher_coeffs: dict[str, float | None]) -> list[dict]:
    out: list[dict] = []
    for row in rows:
        entry = dict(row)
        if row.get('trusted_pair'):
            pred = (
                float(lower_coeffs['m2_gap']) * float(row['m2_gap'])
                + float(lower_coeffs['m2_gap_boundary']) * float(row['m2_gap_boundary'])
                + float(lower_coeffs['area_magnitude']) * float(row['area_magnitude'])
                + float(higher_coeffs['m2_gap_var']) * float(row['m2_gap_var'])
                + float(higher_coeffs['m2_gap_boundary_var']) * float(row['m2_gap_boundary_var'])
                + float(lower_coeffs.get('intercept', 0.0) or 0.0)
            )
            entry['generator_geometry_predictor'] = float(pred)
        else:
            entry['generator_geometry_predictor'] = None
        out.append(entry)
    return out


def _plot_switch_scatter(path: Path, train_rows: list[dict], held_base_rows: list[dict], held_new_rows: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    groups = [('train', train_rows, 'o'), ('held-out base', held_base_rows, 's'), ('held-out new', held_new_rows, '^')]
    for label, rows, marker in groups:
        trusted = [row for row in rows if row.get('generator_geometry_predictor') is not None]
        if not trusted:
            continue
        ax.scatter([float(row['generator_geometry_predictor']) for row in trusted], [float(row['orientation_gap']) for row in trusted], label=label, marker=marker, alpha=0.85)
    ax.set_title('Benchmark C: observed vs generator-geometry predictor @ switch γ')
    ax.set_xlabel('Generator-geometry predictor')
    ax.set_ylabel('Observed orientation gap')
    ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_r2_lines(
    path: Path,
    gammas: list[float],
    base_new: list[float],
    phase26_new: list[float],
    phase27_new: list[float],
    phase28_new: list[float],
    base_combined: list[float],
    phase26_combined: list[float],
    phase27_combined: list[float],
    phase28_combined: list[float],
) -> None:
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    ax.plot(gammas, base_combined, marker='o', label='baseline held-out combined')
    ax.plot(gammas, phase26_combined, marker='s', label='phase26 combined')
    ax.plot(gammas, phase27_combined, marker='^', label='phase27 combined')
    ax.plot(gammas, phase28_combined, marker='d', label='phase28 combined')
    ax.plot(gammas, base_new, marker='o', linestyle='--', label='baseline held-out new')
    ax.plot(gammas, phase26_new, marker='s', linestyle='--', label='phase26 new')
    ax.plot(gammas, phase27_new, marker='^', linestyle='--', label='phase27 new')
    ax.plot(gammas, phase28_new, marker='d', linestyle='--', label='phase28 new')
    ax.set_title('Benchmark C: generator-geometry held-out transfer vs dephasing')
    ax.set_xlabel('Dephasing γ')
    ax.set_ylabel('R²')
    ax.legend(loc='best', ncol=2)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_compactness(path: Path, gammas: list[float], tracks: dict[str, list[float]]) -> None:
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    ax.plot(gammas, tracks['boundary_compactness'], marker='o', label='boundary_compactness')
    ax.plot(gammas, tracks['transport_compactness'], marker='s', label='transport_compactness')
    ax.plot(gammas, tracks['boundary_transport_compactness'], marker='^', label='boundary_transport_compactness')
    ax.plot(gammas, tracks['area_compactness'], marker='d', label='area_compactness')
    ax.set_title('Benchmark C: generator-geometry compactness vs dephasing')
    ax.set_xlabel('Dephasing γ')
    ax.set_ylabel('Compactness')
    ax.legend(loc='best', ncol=2)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def phase28_payload(project_root: Path, config: Phase28Config | None = None) -> dict:
    cfg = config or Phase28Config()
    project_root = Path(project_root)
    bench_dir = project_root / 'cgt_benchmarks' / 'results' / 'benchmark_C_ring'
    source_phase24_path = bench_dir / cfg.source_phase24_filename
    source_phase26_path = bench_dir / cfg.source_phase26_filename
    source_phase27_path = bench_dir / cfg.source_phase27_filename
    if not source_phase24_path.exists():
        raise FileNotFoundError(f'Missing Phase 24 source artifact: {source_phase24_path}')
    if not source_phase26_path.exists():
        raise FileNotFoundError(f'Missing Phase 26 source artifact: {source_phase26_path}')
    if not source_phase27_path.exists():
        raise FileNotFoundError(f'Missing Phase 27 source artifact: {source_phase27_path}')

    phase24 = json.loads(source_phase24_path.read_text())
    phase26 = json.loads(source_phase26_path.read_text())
    phase27 = json.loads(source_phase27_path.read_text())
    phase26_by_gamma = {float(level['dephasing']): level for level in phase26['levels']}
    phase27_by_gamma = {float(level['dephasing']): level for level in phase27['levels']}

    levels_out: list[dict] = []
    gammas: list[float] = []
    base_new_track: list[float] = []
    phase26_new_track: list[float] = []
    phase27_new_track: list[float] = []
    phase28_new_track: list[float] = []
    base_combined_track: list[float] = []
    phase26_combined_track: list[float] = []
    phase27_combined_track: list[float] = []
    phase28_combined_track: list[float] = []
    compactness_tracks = {
        'boundary_compactness': [],
        'transport_compactness': [],
        'boundary_transport_compactness': [],
        'area_compactness': [],
    }

    for source_level in phase24['levels']:
        gamma = float(source_level['dephasing'])
        rows = [copy.deepcopy(row) for row in source_level['rows']]
        train_rows = [row for row in rows if row.get('family_group') == 'train' and row.get('trusted_pair')]
        lower = derive_generator_geometry_lower_order_coefficients(train_rows)
        higher = derive_higher_order_coefficients(train_rows, lower['coefficients'])
        augmented = _augment_rows(rows, lower['coefficients'], higher['coefficients'])

        train_aug = [row for row in augmented if row.get('family_group') == 'train']
        held_base_aug = [row for row in augmented if row.get('family_group') == 'heldout_base']
        held_new_aug = [row for row in augmented if row.get('family_group') == 'heldout_new']
        held_combined_aug = [row for row in augmented if row.get('family_group') != 'train']
        phase26_level = phase26_by_gamma[gamma]
        phase27_level = phase27_by_gamma[gamma]

        level_out = {
            'dephasing': gamma,
            'generator_geometry_lower_order': {
                'coefficients': lower['coefficients'],
                'generator_moments': lower['generator_moments'],
                'compactness': lower['compactness'],
                'derivation': lower['derivation'],
            },
            'generator_geometry_higher_order': {
                'coefficients': higher['coefficients'],
                'generator_moments': higher['generator_moments'],
                'derivation': higher['derivation'],
            },
            'source_phase24_baseline_model': source_level['baseline_model'],
            'source_phase26_generator_normalized': {
                'lower_order': phase26_level['generator_normalized_lower_order'],
                'higher_order': phase26_level['generator_normalized_higher_order'],
                'heldout_new_fit': phase26_level['heldout_new_fit'],
                'heldout_combined_fit': phase26_level['heldout_combined_fit'],
            },
            'source_phase27_moment_normalized': {
                'lower_order': phase27_level['moment_normalized_lower_order'],
                'higher_order': phase27_level['moment_normalized_higher_order'],
                'heldout_new_fit': phase27_level['heldout_new_fit'],
                'heldout_combined_fit': phase27_level['heldout_combined_fit'],
            },
            'train_fit': _prediction_summary(train_aug, 'generator_geometry_predictor'),
            'heldout_base_fit': _prediction_summary(held_base_aug, 'generator_geometry_predictor'),
            'heldout_new_fit': _prediction_summary(held_new_aug, 'generator_geometry_predictor'),
            'heldout_combined_fit': _prediction_summary(held_combined_aug, 'generator_geometry_predictor'),
            'rows': augmented,
        }
        levels_out.append(level_out)
        gammas.append(gamma)

        base_new_track.append(float('nan') if source_level['baseline_model']['heldout_new_fit']['r2'] is None else float(source_level['baseline_model']['heldout_new_fit']['r2']))
        phase26_new_track.append(float('nan') if phase26_level['heldout_new_fit']['r2'] is None else float(phase26_level['heldout_new_fit']['r2']))
        phase27_new_track.append(float('nan') if phase27_level['heldout_new_fit']['r2'] is None else float(phase27_level['heldout_new_fit']['r2']))
        phase28_new_track.append(float('nan') if level_out['heldout_new_fit']['r2'] is None else float(level_out['heldout_new_fit']['r2']))
        base_combined_track.append(float('nan') if source_level['baseline_model']['heldout_combined_fit']['r2'] is None else float(source_level['baseline_model']['heldout_combined_fit']['r2']))
        phase26_combined_track.append(float('nan') if phase26_level['heldout_combined_fit']['r2'] is None else float(phase26_level['heldout_combined_fit']['r2']))
        phase27_combined_track.append(float('nan') if phase27_level['heldout_combined_fit']['r2'] is None else float(phase27_level['heldout_combined_fit']['r2']))
        phase28_combined_track.append(float('nan') if level_out['heldout_combined_fit']['r2'] is None else float(level_out['heldout_combined_fit']['r2']))
        for key in compactness_tracks:
            compactness_tracks[key].append(float(lower['compactness'][key]))

    switch_level = min(levels_out, key=lambda row: abs(float(row['dephasing']) - cfg.default_switch_gamma))
    metrics = {
        'baseline_heldout_new_r2': switch_level['source_phase24_baseline_model']['heldout_new_fit']['r2'],
        'baseline_heldout_combined_r2': switch_level['source_phase24_baseline_model']['heldout_combined_fit']['r2'],
        'phase26_heldout_new_r2': switch_level['source_phase26_generator_normalized']['heldout_new_fit']['r2'],
        'phase26_heldout_combined_r2': switch_level['source_phase26_generator_normalized']['heldout_combined_fit']['r2'],
        'phase27_heldout_new_r2': switch_level['source_phase27_moment_normalized']['heldout_new_fit']['r2'],
        'phase27_heldout_combined_r2': switch_level['source_phase27_moment_normalized']['heldout_combined_fit']['r2'],
        'phase28_heldout_new_r2': switch_level['heldout_new_fit']['r2'],
        'phase28_heldout_combined_r2': switch_level['heldout_combined_fit']['r2'],
        'phase28_heldout_combined_corr': switch_level['heldout_combined_fit']['corr'],
        'phase28_heldout_combined_sign_agreement': switch_level['heldout_combined_fit']['sign_agreement'],
    }

    verdict = 'generator_geometry_normalizers_mixed'
    p27_new = metrics['phase27_heldout_new_r2']
    p27_comb = metrics['phase27_heldout_combined_r2']
    p28_new = metrics['phase28_heldout_new_r2']
    p28_comb = metrics['phase28_heldout_combined_r2']
    if all(v is not None for v in (p27_new, p27_comb, p28_new, p28_comb)):
        if float(p28_new) >= float(p27_new) and float(p28_comb) >= float(p27_comb):
            verdict = 'generator_geometry_normalizers_supported'
        elif float(p28_new) >= float(p27_new):
            verdict = 'generator_geometry_new_family_supported'
        elif float(p28_comb) >= float(p27_comb):
            verdict = 'generator_geometry_combined_supported'
        else:
            verdict = 'generator_geometry_normalizers_mixed'

    payload = {
        'phase': 'phase28_generator_geometry_normalization',
        'benchmark': cfg.benchmark_focus,
        'slug': 'benchmark_C_ring',
        'description': phase24.get('description', 'Three-node ring first positive signed-loop benchmark.'),
        'source_phase24_artifact': str(source_phase24_path.relative_to(project_root)),
        'source_phase26_artifact': str(source_phase26_path.relative_to(project_root)),
        'source_phase27_artifact': str(source_phase27_path.relative_to(project_root)),
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
            'Phase 28 keeps the broadened held-out loop set fixed from Phase 27.',
            'The lower-order noisy coefficients are rebuilt from generator-geometry compactness ratios computed only from canonical train-row moments.',
            'The earlier half-share style inside the Phase 27 normalizers is replaced by compactness-derived gap and boundary factors plus a symmetry-averaged area factor.',
            'The higher-order coefficients remain generator-derived from those lower-order coefficients and train-row generator moments.',
            'No new response regression is introduced in the coefficient step.',
        ],
        'verdict': verdict,
        'switch_metrics': metrics,
    }

    out_path = bench_dir / 'benchmark_c_phase28_generator_geometry_share.json'
    out_path.write_text(json.dumps(payload, indent=2))

    plots_dir = project_root / 'cgt_benchmarks' / 'reports' / 'plots' / 'phase28_generator_geometry' / 'benchmark_C_ring'
    train_rows = [row for row in switch_level['rows'] if row.get('family_group') == 'train']
    held_base_rows = [row for row in switch_level['rows'] if row.get('family_group') == 'heldout_base']
    held_new_rows = [row for row in switch_level['rows'] if row.get('family_group') == 'heldout_new']
    _plot_switch_scatter(plots_dir / 'response_vs_generator_geometry_predictor_switch.png', train_rows, held_base_rows, held_new_rows)
    _plot_r2_lines(
        plots_dir / 'heldout_r2_vs_dephasing.png',
        gammas,
        base_new_track,
        phase26_new_track,
        phase27_new_track,
        phase28_new_track,
        base_combined_track,
        phase26_combined_track,
        phase27_combined_track,
        phase28_combined_track,
    )
    _plot_compactness(plots_dir / 'compactness_vs_dephasing.png', gammas, compactness_tracks)

    summary_path = project_root / 'cgt_benchmarks' / 'reports' / 'phase28_summary.json'
    summary_path.write_text(json.dumps(payload, indent=2))
    return payload
