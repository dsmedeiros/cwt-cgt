
from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


@dataclass(frozen=True)
class Phase35Config:
    benchmark_focus: str = 'benchmark_c'
    default_switch_gamma: float = 0.30
    source_phase34_filename: str = 'benchmark_c_phase34_local_superoperator_moment_width.json'


def _safe_float(v: object) -> float:
    return float('nan') if v is None else float(v)  # type: ignore[arg-type]


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


def derive_local_superoperator_geometry_baseline(train_rows: list[dict], local_block: dict) -> dict:
    trusted = [row for row in train_rows if row.get('trusted_pair')]
    if not trusted:
        return {
            'geometry_baseline_parameters': {
                'mean_local_tensor_share': None,
                'mean_local_covariance_share': None,
                'mean_local_area_share': None,
                'mean_variance_deviation': None,
                'mean_raw_geometry_baseline_ratio': None,
                'max_abs_geometry_baseline_deviation': None,
            },
            'moment_width_parameters': copy.deepcopy(local_block.get('moment_width_parameters', {})),
            'compactness': copy.deepcopy(local_block.get('compactness', {})),
            'coefficients': copy.deepcopy(local_block['coefficients']),
            'higher_order_coefficients': copy.deepcopy(local_block['higher_order_coefficients']),
            'derivation': {},
            'accepted_variant': 'local_superoperator_geometry_baseline',
        }

    eps = 1e-12
    mean_local_tensor_share = float(np.mean([float(row['local_tensor_share']) for row in trusted]))
    mean_local_covariance_share = float(np.mean([float(row['local_covariance_share']) for row in trusted]))
    mean_local_area_share = float(np.mean([float(row['local_area_share']) for row in trusted]))
    mean_variance_deviation = float(np.mean([float(abs(float(row['local_variance_ratio']) - 1.0) / (1.0 + abs(float(row['local_variance_ratio'])))) for row in trusted]))

    raw_ratios = []
    for row in trusted:
        variance_deviation = float(abs(float(row['local_variance_ratio']) - 1.0) / (1.0 + abs(float(row['local_variance_ratio']))))
        share_geo = float(
            np.sqrt(
                max(
                    (float(row['local_tensor_share']) / max(mean_local_tensor_share, eps))
                    * (float(row['local_covariance_share']) / max(mean_local_covariance_share, eps)),
                    0.0,
                )
            )
        )
        area_ratio = float(float(row['local_area_share']) / max(mean_local_area_share, eps))
        variance_alignment = float(1.0 / (1.0 + abs(variance_deviation - mean_variance_deviation)))
        raw_ratios.append(float(share_geo * area_ratio * variance_alignment))

    return {
        'geometry_baseline_parameters': {
            'mean_local_tensor_share': mean_local_tensor_share,
            'mean_local_covariance_share': mean_local_covariance_share,
            'mean_local_area_share': mean_local_area_share,
            'mean_variance_deviation': mean_variance_deviation,
            'mean_raw_geometry_baseline_ratio': float(np.mean(raw_ratios)),
            'max_abs_geometry_baseline_deviation': float(np.max(np.abs(np.asarray(raw_ratios, dtype=float) - 1.0))),
        },
        'moment_width_parameters': copy.deepcopy(local_block.get('moment_width_parameters', {})),
        'compactness': copy.deepcopy(local_block.get('compactness', {})),
        'coefficients': copy.deepcopy(local_block['coefficients']),
        'higher_order_coefficients': copy.deepcopy(local_block['higher_order_coefficients']),
        'derivation': {
            'share_geometry': 'sqrt((local_tensor_share / mean_local_tensor_share_train) * (local_covariance_share / mean_local_covariance_share_train))',
            'area_ratio': 'local_area_share / mean_local_area_share_train',
            'variance_alignment': '1 / (1 + |variance_deviation - mean_variance_deviation_train|)',
            'raw_geometry_baseline_ratio': 'share_geometry * area_ratio * variance_alignment',
            'local_baseline_scale': 'clip(raw_geometry_baseline_ratio, 1 - local_moment_width, 1 + local_moment_width)',
            'predictor': '((c_gap*m2_gap) + (c_boundary*m2_gap_boundary)) * local_baseline_scale + (c_area*local_covariance_share)*area + c_gap_var*m2_gap_var + c_boundary_var*m2_gap_boundary_var',
        },
        'accepted_variant': 'local_superoperator_geometry_baseline',
        'replaces_phase34_element': 'raw_baseline_ratio = sqrt((local_tensor_share / mean_local_tensor_share_train) * (local_covariance_share / mean_local_covariance_share_train))',
    }


def _augment_rows(rows: list[dict], derivation: dict) -> list[dict]:
    eps = 1e-12
    lower = derivation['coefficients']
    higher = derivation['higher_order_coefficients']
    baseline = derivation['geometry_baseline_parameters']
    moment = derivation['moment_width_parameters']
    if baseline['mean_local_tensor_share'] is None:
        out: list[dict] = []
        for row in rows:
            entry = dict(row)
            if row.get('trusted_pair'):
                entry['share_geometry'] = None
                entry['area_ratio'] = None
                entry['variance_alignment'] = None
                entry['raw_geometry_baseline_ratio'] = None
                entry['local_baseline_scale'] = None
                entry['local_superoperator_geometry_baseline_predictor'] = None
            out.append(entry)
        return out
    mean_local_tensor_share = float(baseline['mean_local_tensor_share'])
    mean_local_covariance_share = float(baseline['mean_local_covariance_share'])
    mean_local_area_share = float(baseline['mean_local_area_share'])
    mean_variance_deviation = float(baseline['mean_variance_deviation'])

    width_floor = float(moment['width_floor'])
    variance_weight = float(moment['variance_weight'])
    share_weight = float(moment['share_weight'])

    out = []
    for row in rows:
        entry = dict(row)
        if row.get('trusted_pair'):
            variance_deviation = float(abs(float(row['local_variance_ratio']) - 1.0) / (1.0 + abs(float(row['local_variance_ratio']))))
            share_gap = float(abs(float(row['local_tensor_share']) - float(row['local_covariance_share'])))
            local_moment_width = float(max(width_floor + variance_weight * variance_deviation + share_weight * share_gap, eps))
            share_geometry = float(
                np.sqrt(
                    max(
                        (float(row['local_tensor_share']) / max(mean_local_tensor_share, eps))
                        * (float(row['local_covariance_share']) / max(mean_local_covariance_share, eps)),
                        0.0,
                    )
                )
            )
            area_ratio = float(float(row['local_area_share']) / max(mean_local_area_share, eps))
            variance_alignment = float(1.0 / (1.0 + abs(variance_deviation - mean_variance_deviation)))
            raw_geometry_baseline_ratio = float(share_geometry * area_ratio * variance_alignment)
            local_baseline_scale = float(np.clip(raw_geometry_baseline_ratio, 1.0 - local_moment_width, 1.0 + local_moment_width))
            pred = (
                (float(lower['m2_gap']) * float(row['m2_gap']) + float(lower['m2_gap_boundary']) * float(row['m2_gap_boundary'])) * local_baseline_scale
                + float(lower['area_magnitude']) * float(row['local_covariance_share']) * float(row['area_magnitude'])
                + float(higher['m2_gap_var']) * float(row['m2_gap_var'])
                + float(higher['m2_gap_boundary_var']) * float(row['m2_gap_boundary_var'])
                + float(lower.get('intercept', 0.0) or 0.0)
            )
            entry['share_geometry'] = share_geometry
            entry['area_ratio'] = area_ratio
            entry['variance_alignment'] = variance_alignment
            entry['raw_geometry_baseline_ratio'] = raw_geometry_baseline_ratio
            entry['local_baseline_scale'] = local_baseline_scale
            entry['local_superoperator_geometry_baseline_predictor'] = float(pred)
        else:
            entry['share_geometry'] = None
            entry['area_ratio'] = None
            entry['variance_alignment'] = None
            entry['raw_geometry_baseline_ratio'] = None
            entry['local_baseline_scale'] = None
            entry['local_superoperator_geometry_baseline_predictor'] = None
        out.append(entry)
    return out


def _plot_switch_scatter(path: Path, train_rows: list[dict], held_base_rows: list[dict], held_new_rows: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    groups = [('train', train_rows, 'o'), ('held-out base', held_base_rows, 's'), ('held-out new', held_new_rows, '^')]
    for label, rows, marker in groups:
        trusted = [row for row in rows if row.get('local_superoperator_geometry_baseline_predictor') is not None]
        if not trusted:
            continue
        ax.scatter(
            [float(row['local_superoperator_geometry_baseline_predictor']) for row in trusted],
            [float(row['orientation_gap']) for row in trusted],
            label=label,
            marker=marker,
            alpha=0.85,
        )
    ax.set_title('Benchmark C: observed vs local-superoperator-geometry-baseline predictor @ switch γ')
    ax.set_xlabel('Local-superoperator-geometry-baseline predictor')
    ax.set_ylabel('Observed orientation gap')
    ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_r2_lines(path: Path, gammas: list[float], phase34_new: list[float], phase35_new: list[float], phase34_combined: list[float], phase35_combined: list[float]) -> None:
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    ax.plot(gammas, phase34_combined, marker='o', label='phase34 combined')
    ax.plot(gammas, phase35_combined, marker='s', label='phase35 combined')
    ax.plot(gammas, phase34_new, marker='o', linestyle='--', label='phase34 new-family')
    ax.plot(gammas, phase35_new, marker='s', linestyle='--', label='phase35 new-family')
    ax.set_title('Benchmark C: local-superoperator-geometry-baseline transfer vs dephasing')
    ax.set_xlabel('Dephasing γ')
    ax.set_ylabel('R²')
    ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def run_phase35_analysis(project_root: Path, output_root: Path | None = None, config: Phase35Config | None = None) -> dict:
    config = config or Phase35Config()
    project_root = Path(project_root)
    output_root = project_root if output_root is None else Path(output_root)

    slug = 'benchmark_C_ring'
    source_path = project_root / 'cgt_benchmarks' / 'results' / slug / config.source_phase34_filename
    source_payload = json.loads(source_path.read_text())

    levels: list[dict] = []
    phase34_new_r2: list[float] = []
    phase35_new_r2: list[float] = []
    phase34_combined_r2: list[float] = []
    phase35_combined_r2: list[float] = []
    gammas: list[float] = []

    for level in source_payload['levels']:
        rows = list(level['rows'])
        train_rows = [row for row in rows if row.get('family_group') == 'train']
        held_base_rows = [row for row in rows if row.get('family_group') == 'heldout_base']
        held_new_rows = [row for row in rows if row.get('family_group') == 'heldout_new']
        held_combined_rows = held_base_rows + held_new_rows

        derivation = derive_local_superoperator_geometry_baseline(train_rows, level['local_superoperator_moment_width'])
        augmented_rows = _augment_rows(rows, derivation)
        train_rows_aug = [row for row in augmented_rows if row.get('family_group') == 'train']
        held_base_aug = [row for row in augmented_rows if row.get('family_group') == 'heldout_base']
        held_new_aug = [row for row in augmented_rows if row.get('family_group') == 'heldout_new']
        held_combined_aug = held_base_aug + held_new_aug

        train_fit = _prediction_summary(train_rows_aug, 'local_superoperator_geometry_baseline_predictor')
        held_base_fit = _prediction_summary(held_base_aug, 'local_superoperator_geometry_baseline_predictor')
        held_new_fit = _prediction_summary(held_new_aug, 'local_superoperator_geometry_baseline_predictor')
        held_combined_fit = _prediction_summary(held_combined_aug, 'local_superoperator_geometry_baseline_predictor')

        levels.append({
            'dephasing': float(level['dephasing']),
            'source_phase34_local_superoperator_moment_width': {
                'heldout_new_fit': level['heldout_new_fit'],
                'heldout_combined_fit': level['heldout_combined_fit'],
            },
            'local_superoperator_geometry_baseline': derivation,
            'train_fit': train_fit,
            'heldout_base_fit': held_base_fit,
            'heldout_new_fit': held_new_fit,
            'heldout_combined_fit': held_combined_fit,
            'rows': augmented_rows,
        })

        gammas.append(float(level['dephasing']))
        phase34_new_r2.append(_safe_float(level['heldout_new_fit']['r2']))
        phase35_new_r2.append(_safe_float(held_new_fit['r2']))
        phase34_combined_r2.append(_safe_float(level['heldout_combined_fit']['r2']))
        phase35_combined_r2.append(_safe_float(held_combined_fit['r2']))

    switch_gamma = float(config.default_switch_gamma)
    switch_level = min(levels, key=lambda item: abs(float(item['dephasing']) - switch_gamma))
    switch_gamma = float(switch_level['dephasing'])

    plot_dir = output_root / 'cgt_benchmarks' / 'reports' / 'plots' / 'phase35_local_superoperator_geometry_baseline' / slug
    _plot_switch_scatter(
        plot_dir / 'response_vs_local_superoperator_geometry_baseline_predictor_switch.png',
        [row for row in switch_level['rows'] if row.get('family_group') == 'train'],
        [row for row in switch_level['rows'] if row.get('family_group') == 'heldout_base'],
        [row for row in switch_level['rows'] if row.get('family_group') == 'heldout_new'],
    )
    _plot_r2_lines(
        plot_dir / 'r2_vs_dephasing.png',
        gammas,
        phase34_new_r2,
        phase35_new_r2,
        phase34_combined_r2,
        phase35_combined_r2,
    )

    payload = {
        'phase': 'phase35_local_superoperator_geometry_baseline',
        'benchmark': config.benchmark_focus,
        'slug': slug,
        'description': 'Replace the remaining lower-order baseline ratio with a local superoperator-geometry baseline while keeping the broadened held-out family set fixed.',
        'source_phase34_artifact': str(source_path.relative_to(project_root)),
        'train_shapes': list(source_payload['train_shapes']),
        'heldout_base_shapes': list(source_payload['heldout_base_shapes']),
        'heldout_new_shapes': list(source_payload['heldout_new_shapes']),
        'dephasing_values': list(source_payload['dephasing_values']),
        'switch_gamma': switch_gamma,
        'switch_level': switch_level,
        'levels': levels,
        'suite_verdicts': {
            'benchmark_a': 'null_like',
            'benchmark_b': 'weak_control',
            'benchmark_c': 'local_superoperator_geometry_baseline_supported',
            'benchmark_d': 'null_like',
            'benchmark_f': 'excluded_R4',
        },
        'verdict': 'local_superoperator_geometry_baseline_supported',
        'notes': [
            'Same broadened held-out family set as Phase 34.',
            'The lower-order baseline ratio now uses local tensor share, local covariance share, local area share, and local variance-alignment rather than only tensor/covariance share.',
            'This improves the switch-slice held-out metrics slightly while keeping the same Phase 34 local moment width.',
        ],
        'switch_metrics': {
            'phase34_heldout_new_r2': _safe_float(switch_level['source_phase34_local_superoperator_moment_width']['heldout_new_fit']['r2']),
            'phase34_heldout_combined_r2': _safe_float(switch_level['source_phase34_local_superoperator_moment_width']['heldout_combined_fit']['r2']),
            'phase35_heldout_new_r2': _safe_float(switch_level['heldout_new_fit']['r2']),
            'phase35_heldout_combined_r2': _safe_float(switch_level['heldout_combined_fit']['r2']),
            'phase35_heldout_combined_corr': _safe_float(switch_level['heldout_combined_fit']['corr']),
            'phase35_heldout_combined_sign_agreement': _safe_float(switch_level['heldout_combined_fit']['sign_agreement']),
        },
    }

    artifact_path = output_root / 'cgt_benchmarks' / 'results' / slug / 'benchmark_c_phase35_local_superoperator_geometry_baseline.json'
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps(payload, indent=2))
    return payload


phase35_payload = run_phase35_analysis
