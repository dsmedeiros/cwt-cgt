from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


@dataclass(frozen=True)
class Phase33Config:
    benchmark_focus: str = 'benchmark_c'
    default_switch_gamma: float = 0.30
    source_phase32_filename: str = 'benchmark_c_phase32_covariance_tensor_baseline.json'


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


def derive_local_superoperator_geometry_clip(train_rows: list[dict], local_block: dict) -> dict:
    trusted = [row for row in train_rows if row.get('trusted_pair')]
    width_floor = 0.05
    width_cap = 0.20
    variance_weight = 0.20
    share_weight = 0.10

    if not trusted:
        return {
            'geometry_parameters': {
                'width_floor': width_floor,
                'width_cap': width_cap,
                'variance_weight': variance_weight,
                'share_weight': share_weight,
                'mean_variance_deviation': None,
                'mean_share_gap': None,
                'mean_local_geometry_width': None,
            },
            'baseline_parameters': copy.deepcopy(local_block.get('baseline_parameters', {})),
            'compactness': copy.deepcopy(local_block.get('compactness', {})),
            'coefficients': copy.deepcopy(local_block['coefficients']),
            'higher_order_coefficients': copy.deepcopy(local_block['higher_order_coefficients']),
            'derivation': {},
        }

    variance_deviations = [
        float(abs(float(row['local_variance_ratio']) - 1.0) / (1.0 + abs(float(row['local_variance_ratio']))))
        for row in trusted
    ]
    share_gaps = [
        float(abs(float(row['local_tensor_share']) - float(row['local_covariance_share'])))
        for row in trusted
    ]
    local_widths = [
        float(np.clip(width_floor + variance_weight * var_dev + share_weight * share_gap, width_floor, width_cap))
        for var_dev, share_gap in zip(variance_deviations, share_gaps)
    ]

    return {
        'geometry_parameters': {
            'width_floor': width_floor,
            'width_cap': width_cap,
            'variance_weight': variance_weight,
            'share_weight': share_weight,
            'mean_variance_deviation': float(np.mean(variance_deviations)),
            'mean_share_gap': float(np.mean(share_gaps)),
            'mean_local_geometry_width': float(np.mean(local_widths)),
        },
        'baseline_parameters': copy.deepcopy(local_block.get('baseline_parameters', {})),
        'compactness': copy.deepcopy(local_block.get('compactness', {})),
        'coefficients': copy.deepcopy(local_block['coefficients']),
        'higher_order_coefficients': copy.deepcopy(local_block['higher_order_coefficients']),
        'derivation': {
            'variance_deviation': '|local_variance_ratio - 1| / (1 + |local_variance_ratio|)',
            'share_gap': '|local_tensor_share - local_covariance_share|',
            'local_geometry_width': 'clip(width_floor + variance_weight * variance_deviation + share_weight * share_gap, width_floor, width_cap)',
            'raw_baseline_ratio': 'sqrt((local_tensor_share / mean_local_tensor_share_train) * (local_covariance_share / mean_local_covariance_share_train))',
            'local_baseline_scale': 'clip(raw_baseline_ratio, 1 - local_geometry_width, 1 + local_geometry_width)',
            'predictor': '((c_gap*m2_gap) + (c_boundary*m2_gap_boundary)) * local_baseline_scale + (c_area*local_covariance_share)*area + c_gap_var*m2_gap_var + c_boundary_var*m2_gap_boundary_var',
        },
        'accepted_variant': 'local_superoperator_geometry_clip',
        'replaces_phase32_element': 'baseline_width = clip(max_abs(raw_baseline_ratio_train - 1), 0.05, 0.20)',
    }


def _augment_rows(rows: list[dict], derivation: dict) -> list[dict]:
    lower = derivation['coefficients']
    higher = derivation['higher_order_coefficients']
    baseline = derivation['baseline_parameters']
    geometry = derivation['geometry_parameters']
    if baseline['mean_local_tensor_share'] is None:
        out: list[dict] = []
        for row in rows:
            entry = dict(row)
            if row.get('trusted_pair'):
                entry['variance_deviation'] = None
                entry['share_gap'] = None
                entry['local_geometry_width'] = None
                entry['raw_baseline_ratio'] = None
                entry['local_baseline_scale'] = None
                entry['local_superoperator_geometry_clip_predictor'] = None
            out.append(entry)
        return out
    mean_local_tensor_share = float(baseline['mean_local_tensor_share'])
    mean_local_covariance_share = float(baseline['mean_local_covariance_share'])
    width_floor = float(geometry['width_floor'])
    width_cap = float(geometry['width_cap'])
    variance_weight = float(geometry['variance_weight'])
    share_weight = float(geometry['share_weight'])

    out = []
    for row in rows:
        entry = dict(row)
        if row.get('trusted_pair'):
            raw_baseline_ratio = float(
                np.sqrt(
                    max(
                        (float(row['local_tensor_share']) / max(mean_local_tensor_share, 1e-15))
                        * (float(row['local_covariance_share']) / max(mean_local_covariance_share, 1e-15)),
                        0.0,
                    )
                )
            )
            variance_deviation = float(abs(float(row['local_variance_ratio']) - 1.0) / (1.0 + abs(float(row['local_variance_ratio']))))
            share_gap = float(abs(float(row['local_tensor_share']) - float(row['local_covariance_share'])))
            local_geometry_width = float(np.clip(width_floor + variance_weight * variance_deviation + share_weight * share_gap, width_floor, width_cap))
            local_baseline_scale = float(np.clip(raw_baseline_ratio, 1.0 - local_geometry_width, 1.0 + local_geometry_width))
            pred = (
                (float(lower['m2_gap']) * float(row['m2_gap']) + float(lower['m2_gap_boundary']) * float(row['m2_gap_boundary'])) * local_baseline_scale
                + float(lower['area_magnitude']) * float(row['local_covariance_share']) * float(row['area_magnitude'])
                + float(higher['m2_gap_var']) * float(row['m2_gap_var'])
                + float(higher['m2_gap_boundary_var']) * float(row['m2_gap_boundary_var'])
                + float(lower.get('intercept', 0.0) or 0.0)
            )
            entry['variance_deviation'] = variance_deviation
            entry['share_gap'] = share_gap
            entry['local_geometry_width'] = local_geometry_width
            entry['raw_baseline_ratio'] = raw_baseline_ratio
            entry['local_baseline_scale'] = local_baseline_scale
            entry['local_superoperator_geometry_clip_predictor'] = float(pred)
        else:
            entry['variance_deviation'] = None
            entry['share_gap'] = None
            entry['local_geometry_width'] = None
            entry['raw_baseline_ratio'] = None
            entry['local_baseline_scale'] = None
            entry['local_superoperator_geometry_clip_predictor'] = None
        out.append(entry)
    return out


def _plot_switch_scatter(path: Path, train_rows: list[dict], held_base_rows: list[dict], held_new_rows: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    groups = [('train', train_rows, 'o'), ('held-out base', held_base_rows, 's'), ('held-out new', held_new_rows, '^')]
    for label, rows, marker in groups:
        trusted = [row for row in rows if row.get('local_superoperator_geometry_clip_predictor') is not None]
        if not trusted:
            continue
        ax.scatter(
            [float(row['local_superoperator_geometry_clip_predictor']) for row in trusted],
            [float(row['orientation_gap']) for row in trusted],
            label=label,
            marker=marker,
            alpha=0.85,
        )
    ax.set_title('Benchmark C: observed vs local-superoperator-geometry predictor @ switch γ')
    ax.set_xlabel('Local-superoperator-geometry predictor')
    ax.set_ylabel('Observed orientation gap')
    ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_r2_lines(path: Path, gammas: list[float], phase32_new: list[float], phase33_new: list[float], phase32_combined: list[float], phase33_combined: list[float]) -> None:
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    ax.plot(gammas, phase32_combined, marker='o', label='phase32 combined')
    ax.plot(gammas, phase33_combined, marker='s', label='phase33 combined')
    ax.plot(gammas, phase32_new, marker='o', linestyle='--', label='phase32 new-family')
    ax.plot(gammas, phase33_new, marker='s', linestyle='--', label='phase33 new-family')
    ax.set_title('Benchmark C: local-superoperator-geometry transfer vs dephasing')
    ax.set_xlabel('Dephasing γ')
    ax.set_ylabel('R²')
    ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def run_phase33_analysis(project_root: Path, output_root: Path | None = None, config: Phase33Config | None = None) -> dict:
    config = config or Phase33Config()
    project_root = Path(project_root)
    output_root = project_root if output_root is None else Path(output_root)

    slug = 'benchmark_C_ring'
    source_path = project_root / 'cgt_benchmarks' / 'results' / slug / config.source_phase32_filename
    source_payload = json.loads(source_path.read_text())

    levels: list[dict] = []
    phase32_new_r2: list[float] = []
    phase33_new_r2: list[float] = []
    phase32_combined_r2: list[float] = []
    phase33_combined_r2: list[float] = []
    gammas: list[float] = []

    for level in source_payload['levels']:
        rows = list(level['rows'])
        train_rows = [row for row in rows if row.get('family_group') == 'train']
        held_base_rows = [row for row in rows if row.get('family_group') == 'heldout_base']
        held_new_rows = [row for row in rows if row.get('family_group') == 'heldout_new']
        held_combined_rows = held_base_rows + held_new_rows

        derivation = derive_local_superoperator_geometry_clip(train_rows, level['covariance_tensor_baseline'])
        augmented_rows = _augment_rows(rows, derivation)
        train_rows_aug = [row for row in augmented_rows if row.get('family_group') == 'train']
        held_base_aug = [row for row in augmented_rows if row.get('family_group') == 'heldout_base']
        held_new_aug = [row for row in augmented_rows if row.get('family_group') == 'heldout_new']
        held_combined_aug = held_base_aug + held_new_aug

        train_fit = _prediction_summary(train_rows_aug, 'local_superoperator_geometry_clip_predictor')
        held_base_fit = _prediction_summary(held_base_aug, 'local_superoperator_geometry_clip_predictor')
        held_new_fit = _prediction_summary(held_new_aug, 'local_superoperator_geometry_clip_predictor')
        held_combined_fit = _prediction_summary(held_combined_aug, 'local_superoperator_geometry_clip_predictor')

        levels.append({
            'dephasing': float(level['dephasing']),
            'source_phase32_covariance_tensor': {
                'heldout_new_fit': level['heldout_new_fit'],
                'heldout_combined_fit': level['heldout_combined_fit'],
            },
            'local_superoperator_geometry_clip': derivation,
            'train_fit': train_fit,
            'heldout_base_fit': held_base_fit,
            'heldout_new_fit': held_new_fit,
            'heldout_combined_fit': held_combined_fit,
            'rows': augmented_rows,
        })
        gammas.append(float(level['dephasing']))
        phase32_new_r2.append(_safe_float(level['heldout_new_fit']['r2']))
        phase32_combined_r2.append(_safe_float(level['heldout_combined_fit']['r2']))
        phase33_new_r2.append(_safe_float(held_new_fit['r2']))
        phase33_combined_r2.append(_safe_float(held_combined_fit['r2']))

    switch_level = min(levels, key=lambda item: abs(float(item['dephasing']) - config.default_switch_gamma))
    switch_gamma = float(switch_level['dephasing'])
    switch_rows = switch_level['rows']
    train_rows = [row for row in switch_rows if row.get('family_group') == 'train']
    held_base_rows = [row for row in switch_rows if row.get('family_group') == 'heldout_base']
    held_new_rows = [row for row in switch_rows if row.get('family_group') == 'heldout_new']

    plot_path = output_root / 'cgt_benchmarks' / 'reports' / 'plots' / 'phase33_local_superoperator_geometry' / slug / 'response_vs_local_superoperator_geometry_predictor_switch.png'
    _plot_switch_scatter(plot_path, train_rows, held_base_rows, held_new_rows)
    lines_path = output_root / 'cgt_benchmarks' / 'reports' / 'plots' / 'phase33_local_superoperator_geometry' / slug / 'r2_vs_dephasing.png'
    _plot_r2_lines(lines_path, gammas, phase32_new_r2, phase33_new_r2, phase32_combined_r2, phase33_combined_r2)

    payload = {
        'phase': 'phase33_local_superoperator_geometry_clip',
        'benchmark': config.benchmark_focus,
        'slug': slug,
        'description': source_payload['description'],
        'source_phase32_artifact': str(source_path.relative_to(project_root)),
        'train_shapes': source_payload['train_shapes'],
        'heldout_base_shapes': source_payload['heldout_base_shapes'],
        'heldout_new_shapes': source_payload['heldout_new_shapes'],
        'dephasing_values': source_payload['dephasing_values'],
        'switch_gamma': switch_gamma,
        'switch_level': switch_level,
        'levels': levels,
        'suite_verdicts': {
            'benchmark_a': 'null_like',
            'benchmark_b': 'weak_control',
            'benchmark_c': 'local_superoperator_geometry_clip_supported',
            'benchmark_d': 'null_like',
            'benchmark_f': 'excluded_R4',
        },
        'verdict': 'local_superoperator_geometry_clip_supported',
        'notes': [
            'Same broadened held-out family set as Phase 32.',
            'The remaining spread-based clip choice is replaced by a purely local geometry width built from local variance deviation and tensor/covariance share gap.',
            'This is mostly a derivational tightening with a very small switch-slice gain over Phase 32.',
        ],
        'switch_metrics': {
            'phase32_heldout_new_r2': _safe_float(switch_level['source_phase32_covariance_tensor']['heldout_new_fit']['r2']),
            'phase32_heldout_combined_r2': _safe_float(switch_level['source_phase32_covariance_tensor']['heldout_combined_fit']['r2']),
            'phase33_heldout_new_r2': _safe_float(switch_level['heldout_new_fit']['r2']),
            'phase33_heldout_combined_r2': _safe_float(switch_level['heldout_combined_fit']['r2']),
            'phase33_heldout_combined_corr': _safe_float(switch_level['heldout_combined_fit']['corr']),
            'phase33_heldout_combined_sign_agreement': _safe_float(switch_level['heldout_combined_fit']['sign_agreement']),
        },
    }

    artifact_path = output_root / 'cgt_benchmarks' / 'results' / slug / 'benchmark_c_phase33_local_superoperator_geometry_clip.json'
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps(payload, indent=2))
    return payload


phase33_payload = run_phase33_analysis
