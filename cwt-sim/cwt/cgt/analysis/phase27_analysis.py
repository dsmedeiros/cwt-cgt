from __future__ import annotations

import copy
import json
import math
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


@dataclass(frozen=True)
class Phase27Config:
    benchmark_focus: str = 'benchmark_c'
    default_switch_gamma: float = 0.30
    source_phase24_filename: str = 'benchmark_c_phase24_clean_rerun_higher_order.json'
    source_phase25_filename: str = 'benchmark_c_phase25_moment_derived_higher_order.json'
    source_phase26_filename: str = 'benchmark_c_phase26_generator_normalized_transfer.json'


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


def derive_moment_normalized_lower_order_coefficients(train_rows: list[dict]) -> dict:
    trusted = [row for row in train_rows if row.get('trusted_pair')]
    if not trusted:
        return {
            'coefficients': {'m2_gap': None, 'm2_gap_boundary': None, 'area_magnitude': None, 'intercept': None},
            'moments': {},
            'normalizers': {},
            'derivation': {},
        }

    mean_abs_boundary = float(np.mean(np.abs([float(row['boundary_distance_u']) for row in trusted])))
    mean_abs_gap = float(np.mean(np.abs([float(row['m2_gap']) for row in trusted])))
    mean_abs_gap_boundary = float(np.mean(np.abs([float(row['m2_gap_boundary']) for row in trusted])))
    mean_abs_area = float(np.mean(np.abs([float(row['area_magnitude']) for row in trusted])))
    mean_signed_gap = abs(float(np.mean([float(row['m2_gap']) for row in trusted])))

    polarization = mean_signed_gap / max(mean_abs_gap, 1e-15)
    boundary_ratio = mean_signed_gap / max(mean_abs_gap_boundary, 1e-15)

    gap_share_normalizer = mean_abs_gap_boundary / max(2.0 * (mean_abs_gap_boundary + mean_signed_gap), 1e-15)
    boundary_geometric_normalizer = math.sqrt(mean_abs_gap_boundary / max(mean_abs_gap, 1e-15)) + polarization
    area_structure_normalizer = boundary_ratio - 0.5 * polarization

    coeff_gap = gap_share_normalizer * mean_abs_boundary * (1.0 - polarization)
    coeff_gap_boundary = boundary_geometric_normalizer * mean_abs_boundary * (boundary_ratio ** 3)
    coeff_area = -area_structure_normalizer * math.sqrt(mean_abs_gap * mean_abs_gap_boundary) / max(mean_abs_area, 1e-15)

    return {
        'coefficients': {
            'm2_gap': float(coeff_gap),
            'm2_gap_boundary': float(coeff_gap_boundary),
            'area_magnitude': float(coeff_area),
            'intercept': 0.0,
        },
        'moments': {
            'mean_abs_boundary_distance': mean_abs_boundary,
            'mean_abs_m2_gap': mean_abs_gap,
            'mean_abs_m2_gap_boundary': mean_abs_gap_boundary,
            'mean_abs_area_magnitude': mean_abs_area,
            'mean_signed_m2_gap': mean_signed_gap,
            'polarization': polarization,
            'boundary_ratio': boundary_ratio,
        },
        'normalizers': {
            'gap_share_normalizer': gap_share_normalizer,
            'boundary_geometric_normalizer': boundary_geometric_normalizer,
            'area_structure_normalizer': area_structure_normalizer,
        },
        'derivation': {
            'gap_share_normalizer': 'mean_abs(m2_gap_boundary) / (2 * (mean_abs(m2_gap_boundary) + mean_signed(m2_gap)))',
            'boundary_geometric_normalizer': 'sqrt(mean_abs(m2_gap_boundary) / mean_abs(m2_gap)) + polarization',
            'area_structure_normalizer': 'boundary_ratio - polarization / 2',
            'm2_gap': 'gap_share_normalizer * mean_abs_boundary_distance * (1 - polarization)',
            'm2_gap_boundary': 'boundary_geometric_normalizer * mean_abs_boundary_distance * boundary_ratio^3',
            'area_magnitude': '-area_structure_normalizer * sqrt(mean_abs(m2_gap) * mean_abs(m2_gap_boundary)) / mean_abs(area)',
            'intercept': '0.0',
        },
    }


def derive_higher_order_coefficients(train_rows: list[dict], lower_coefficients: dict[str, float | None]) -> dict:
    trusted = [row for row in train_rows if row.get('trusted_pair')]
    if not trusted:
        return {
            'coefficients': {'m2_gap_var': None, 'm2_gap_boundary_var': None},
            'moments': {},
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
        'moments': {
            'mean_abs_m2_gap': mean_abs_gap,
            'mean_abs_m2_gap_boundary': mean_abs_gap_boundary,
            'mean_abs_area_magnitude': mean_abs_area,
            'mean_abs_m2_gap_var': mean_abs_gap_var,
            'mean_abs_m2_gap_boundary_var': mean_abs_gap_boundary_var,
        },
        'derivation': {
            'm2_gap_var': '-|c_gap^(moment-normalized)| * mean_abs(m2_gap) / mean_abs(m2_gap_var)',
            'm2_gap_boundary_var': '+sqrt(|c_boundary^(moment-normalized)| mean_abs(m2_gap_boundary) * |c_area^(moment-normalized)| mean_abs(area)) / mean_abs(m2_gap_boundary_var)',
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
            entry['moment_normalized_predictor'] = float(pred)
        else:
            entry['moment_normalized_predictor'] = None
        out.append(entry)
    return out


def _plot_switch_scatter(path: Path, train_rows: list[dict], held_base_rows: list[dict], held_new_rows: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    groups = [('train', train_rows, 'o'), ('held-out base', held_base_rows, 's'), ('held-out new', held_new_rows, '^')]
    for label, rows, marker in groups:
        trusted = [row for row in rows if row.get('moment_normalized_predictor') is not None]
        if not trusted:
            continue
        ax.scatter([float(row['moment_normalized_predictor']) for row in trusted], [float(row['orientation_gap']) for row in trusted], label=label, marker=marker, alpha=0.85)
    ax.set_title('Benchmark C: observed vs moment-normalized predictor @ switch γ')
    ax.set_xlabel('Moment-normalized predictor')
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
    phase25_new: list[float],
    phase26_new: list[float],
    phase27_new: list[float],
    base_combined: list[float],
    phase25_combined: list[float],
    phase26_combined: list[float],
    phase27_combined: list[float],
) -> None:
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    ax.plot(gammas, base_combined, marker='o', label='baseline held-out combined')
    ax.plot(gammas, phase25_combined, marker='s', label='phase25 combined')
    ax.plot(gammas, phase26_combined, marker='^', label='phase26 combined')
    ax.plot(gammas, phase27_combined, marker='d', label='phase27 combined')
    ax.plot(gammas, base_new, marker='o', linestyle='--', label='baseline held-out new')
    ax.plot(gammas, phase25_new, marker='s', linestyle='--', label='phase25 new')
    ax.plot(gammas, phase26_new, marker='^', linestyle='--', label='phase26 new')
    ax.plot(gammas, phase27_new, marker='d', linestyle='--', label='phase27 new')
    ax.set_title('Benchmark C: moment-normalized held-out transfer vs dephasing')
    ax.set_xlabel('Dephasing γ')
    ax.set_ylabel('R²')
    ax.legend(loc='best', ncol=2)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_normalizers(path: Path, gammas: list[float], tracks: dict[str, list[float]]) -> None:
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    ax.plot(gammas, tracks['gap_share_normalizer'], marker='o', label='gap_share_normalizer')
    ax.plot(gammas, tracks['boundary_geometric_normalizer'], marker='s', label='boundary_geometric_normalizer')
    ax.plot(gammas, tracks['area_structure_normalizer'], marker='^', label='area_structure_normalizer')
    ax.set_title('Benchmark C: moment normalizers vs dephasing')
    ax.set_xlabel('Dephasing γ')
    ax.set_ylabel('Normalizer value')
    ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def phase27_payload(project_root: Path, config: Phase27Config | None = None) -> dict:
    cfg = config or Phase27Config()
    project_root = Path(project_root)
    bench_dir = project_root / 'cgt_benchmarks' / 'results' / 'benchmark_C_ring'
    source_phase24_path = bench_dir / cfg.source_phase24_filename
    source_phase25_path = bench_dir / cfg.source_phase25_filename
    source_phase26_path = bench_dir / cfg.source_phase26_filename
    if not source_phase24_path.exists():
        raise FileNotFoundError(f'Missing Phase 24 source artifact: {source_phase24_path}')
    if not source_phase25_path.exists():
        raise FileNotFoundError(f'Missing Phase 25 source artifact: {source_phase25_path}')
    if not source_phase26_path.exists():
        raise FileNotFoundError(f'Missing Phase 26 source artifact: {source_phase26_path}')

    phase24 = json.loads(source_phase24_path.read_text())
    phase25 = json.loads(source_phase25_path.read_text())
    phase26 = json.loads(source_phase26_path.read_text())
    phase25_by_gamma = {float(level['dephasing']): level for level in phase25['levels']}
    phase26_by_gamma = {float(level['dephasing']): level for level in phase26['levels']}

    levels_out: list[dict] = []
    gammas: list[float] = []
    base_new_track: list[float] = []
    phase25_new_track: list[float] = []
    phase26_new_track: list[float] = []
    phase27_new_track: list[float] = []
    base_combined_track: list[float] = []
    phase25_combined_track: list[float] = []
    phase26_combined_track: list[float] = []
    phase27_combined_track: list[float] = []
    normalizer_tracks = {
        'gap_share_normalizer': [],
        'boundary_geometric_normalizer': [],
        'area_structure_normalizer': [],
    }

    for source_level in phase24['levels']:
        gamma = float(source_level['dephasing'])
        rows = [copy.deepcopy(row) for row in source_level['rows']]
        train_rows = [row for row in rows if row.get('family_group') == 'train' and row.get('trusted_pair')]
        lower = derive_moment_normalized_lower_order_coefficients(train_rows)
        higher = derive_higher_order_coefficients(train_rows, lower['coefficients'])
        augmented = _augment_rows(rows, lower['coefficients'], higher['coefficients'])

        train_aug = [row for row in augmented if row.get('family_group') == 'train']
        held_base_aug = [row for row in augmented if row.get('family_group') == 'heldout_base']
        held_new_aug = [row for row in augmented if row.get('family_group') == 'heldout_new']
        held_combined_aug = [row for row in augmented if row.get('family_group') != 'train']
        phase25_level = phase25_by_gamma[gamma]
        phase26_level = phase26_by_gamma[gamma]

        level_out = {
            'dephasing': gamma,
            'moment_normalized_lower_order': {
                'coefficients': lower['coefficients'],
                'generator_moments': lower['moments'],
                'normalizers': lower['normalizers'],
                'derivation': lower['derivation'],
            },
            'moment_normalized_higher_order': {
                'coefficients': higher['coefficients'],
                'generator_moments': higher['moments'],
                'derivation': higher['derivation'],
            },
            'source_phase24_baseline_model': source_level['baseline_model'],
            'source_phase25_moment_derived_higher_order': phase25_level['moment_derived_higher_order'],
            'source_phase26_generator_normalized': {
                'lower_order': phase26_level['generator_normalized_lower_order'],
                'higher_order': phase26_level['generator_normalized_higher_order'],
                'heldout_new_fit': phase26_level['heldout_new_fit'],
                'heldout_combined_fit': phase26_level['heldout_combined_fit'],
            },
            'train_fit': _prediction_summary(train_aug, 'moment_normalized_predictor'),
            'heldout_base_fit': _prediction_summary(held_base_aug, 'moment_normalized_predictor'),
            'heldout_new_fit': _prediction_summary(held_new_aug, 'moment_normalized_predictor'),
            'heldout_combined_fit': _prediction_summary(held_combined_aug, 'moment_normalized_predictor'),
            'rows': augmented,
        }
        levels_out.append(level_out)
        gammas.append(gamma)

        base_new_track.append(float('nan') if source_level['baseline_model']['heldout_new_fit']['r2'] is None else float(source_level['baseline_model']['heldout_new_fit']['r2']))
        phase25_new_track.append(float('nan') if phase25_level['moment_derived_higher_order']['heldout_new_fit']['r2'] is None else float(phase25_level['moment_derived_higher_order']['heldout_new_fit']['r2']))
        phase26_new_track.append(float('nan') if phase26_level['heldout_new_fit']['r2'] is None else float(phase26_level['heldout_new_fit']['r2']))
        phase27_new_track.append(float('nan') if level_out['heldout_new_fit']['r2'] is None else float(level_out['heldout_new_fit']['r2']))
        base_combined_track.append(float('nan') if source_level['baseline_model']['heldout_combined_fit']['r2'] is None else float(source_level['baseline_model']['heldout_combined_fit']['r2']))
        phase25_combined_track.append(float('nan') if phase25_level['moment_derived_higher_order']['heldout_combined_fit']['r2'] is None else float(phase25_level['moment_derived_higher_order']['heldout_combined_fit']['r2']))
        phase26_combined_track.append(float('nan') if phase26_level['heldout_combined_fit']['r2'] is None else float(phase26_level['heldout_combined_fit']['r2']))
        phase27_combined_track.append(float('nan') if level_out['heldout_combined_fit']['r2'] is None else float(level_out['heldout_combined_fit']['r2']))
        normalizer_tracks['gap_share_normalizer'].append(float(lower['normalizers']['gap_share_normalizer']))
        normalizer_tracks['boundary_geometric_normalizer'].append(float(lower['normalizers']['boundary_geometric_normalizer']))
        normalizer_tracks['area_structure_normalizer'].append(float(lower['normalizers']['area_structure_normalizer']))

    switch_level = min(levels_out, key=lambda row: abs(float(row['dephasing']) - cfg.default_switch_gamma))
    base_new = switch_level['source_phase24_baseline_model']['heldout_new_fit']['r2']
    base_comb = switch_level['source_phase24_baseline_model']['heldout_combined_fit']['r2']
    phase25_new = switch_level['source_phase25_moment_derived_higher_order']['heldout_new_fit']['r2']
    phase25_comb = switch_level['source_phase25_moment_derived_higher_order']['heldout_combined_fit']['r2']
    phase26_new = switch_level['source_phase26_generator_normalized']['heldout_new_fit']['r2']
    phase26_comb = switch_level['source_phase26_generator_normalized']['heldout_combined_fit']['r2']
    phase27_new = switch_level['heldout_new_fit']['r2']
    phase27_comb = switch_level['heldout_combined_fit']['r2']

    verdict = 'moment_normalizer_transfer_uncertain'
    if all(val is not None for val in (phase27_new, phase27_comb, phase26_new, phase26_comb)):
        if float(phase27_new) >= float(phase26_new) and float(phase27_comb) >= float(phase26_comb):
            verdict = 'moment_normalizer_transfer_supported'
        elif float(phase27_new) >= float(phase26_new):
            verdict = 'moment_normalizer_new_family_supported'
        elif float(phase27_comb) >= float(phase26_comb):
            verdict = 'moment_normalizer_combined_supported'
        else:
            verdict = 'moment_normalizer_transfer_mixed'

    payload = {
        'phase': 'phase27_moment_normalized_transfer',
        'benchmark': cfg.benchmark_focus,
        'slug': 'benchmark_C_ring',
        'description': phase24.get('description', 'Three-node ring first positive signed-loop benchmark.'),
        'source_phase24_artifact': str(source_phase24_path.relative_to(project_root)),
        'source_phase25_artifact': str(source_phase25_path.relative_to(project_root)),
        'source_phase26_artifact': str(source_phase26_path.relative_to(project_root)),
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
            'Phase 27 keeps the clean Phase 24 broadened held-out loop set fixed.',
            'The lower-order noisy coefficients are rebuilt from local generator moments using moment-varying normalizers rather than the fixed structural normalizers used in Phase 26.',
            'The higher-order coefficients remain generator-derived from the moment-normalized lower-order coefficients and canonical generator moments.',
            'No response refit is introduced in this pass; the main change is replacing the remaining fixed lower-order structural constants with moment-derived normalizers.',
            'The remaining boundary is that the half-share split in the gap and area normalizers is still a structural modeling choice rather than a fully analytic microscopic derivation.',
        ],
        'verdict': verdict,
        'switch_metrics': {
            'baseline_heldout_new_r2': base_new,
            'baseline_heldout_combined_r2': base_comb,
            'phase25_heldout_new_r2': phase25_new,
            'phase25_heldout_combined_r2': phase25_comb,
            'phase26_heldout_new_r2': phase26_new,
            'phase26_heldout_combined_r2': phase26_comb,
            'phase27_heldout_new_r2': phase27_new,
            'phase27_heldout_combined_r2': phase27_comb,
            'phase27_heldout_combined_corr': switch_level['heldout_combined_fit']['corr'],
            'phase27_heldout_combined_sign_agreement': switch_level['heldout_combined_fit']['sign_agreement'],
        },
    }

    out_path = bench_dir / 'benchmark_c_phase27_moment_normalized_transfer.json'
    out_path.write_text(json.dumps(payload, indent=2))

    plots_dir = project_root / 'cgt_benchmarks' / 'reports' / 'plots' / 'phase27_moment_normalized' / 'benchmark_C_ring'
    train_rows = [row for row in switch_level['rows'] if row.get('family_group') == 'train']
    held_base_rows = [row for row in switch_level['rows'] if row.get('family_group') == 'heldout_base']
    held_new_rows = [row for row in switch_level['rows'] if row.get('family_group') == 'heldout_new']
    _plot_switch_scatter(plots_dir / 'response_vs_moment_normalized_predictor_switch.png', train_rows, held_base_rows, held_new_rows)
    _plot_r2_lines(
        plots_dir / 'heldout_r2_vs_dephasing.png',
        gammas,
        base_new_track,
        phase25_new_track,
        phase26_new_track,
        phase27_new_track,
        base_combined_track,
        phase25_combined_track,
        phase26_combined_track,
        phase27_combined_track,
    )
    _plot_normalizers(plots_dir / 'moment_normalizers_vs_dephasing.png', gammas, normalizer_tracks)

    summary_path = project_root / 'cgt_benchmarks' / 'reports' / 'phase27_summary.json'
    summary_path.write_text(json.dumps(payload, indent=2))
    return payload
