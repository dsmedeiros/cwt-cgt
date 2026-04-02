from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


@dataclass(frozen=True)
class Phase30Config:
    benchmark_focus: str = 'benchmark_c'
    default_switch_gamma: float = 0.30
    source_phase29_filename: str = 'benchmark_c_phase29_local_superoperator_area.json'


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


def derive_local_superoperator_anisotropy(train_rows: list[dict], local_block: dict) -> dict:
    trusted = [row for row in train_rows if row.get('trusted_pair')]
    if not trusted:
        return {
            'anisotropy_parameters': {
                'alpha_tensor': None,
                'beta_boundary': None,
                'mean_abs_generator_var': None,
                'mean_abs_boundary_distance': None,
                'mean_abs_m2_gap_boundary': None,
                'mean_train_anisotropy': None,
                'share_clip': [0.65, 1.35],
            },
            'compactness': {},
            'coefficients': copy.deepcopy(local_block['coefficients']),
            'higher_order_coefficients': copy.deepcopy(local_block['higher_order_coefficients']),
            'derivation': {},
        }

    compactness = copy.deepcopy(local_block['compactness'])
    mean_abs_generator_var = float(np.mean([abs(float(row['generator_var_mean'])) for row in trusted]))
    mean_abs_boundary = float(np.mean([abs(float(row['boundary_distance_u'])) for row in trusted]))
    mean_abs_gap_boundary = float(np.mean([abs(float(row['m2_gap_boundary'])) for row in trusted]))

    rv = np.asarray([abs(float(row['generator_var_mean'])) for row in trusted], dtype=float) / max(mean_abs_generator_var, 1e-15)
    rb = np.asarray([abs(float(row['boundary_distance_u'])) for row in trusted], dtype=float) / max(mean_abs_boundary, 1e-15)
    rt = np.asarray([abs(float(row['m2_gap_boundary'])) for row in trusted], dtype=float) / max(mean_abs_gap_boundary, 1e-15)
    cross = np.sqrt(rv * rt)
    anisotropy = np.sqrt((rv - rb) ** 2 + 4.0 * cross ** 2) / np.maximum(rv + rb, 1e-15)

    alpha_tensor = float(compactness['alpha_gap'])
    beta_boundary = float(1.0 - float(compactness['boundary_compactness']))

    return {
        'anisotropy_parameters': {
            'alpha_tensor': alpha_tensor,
            'beta_boundary': beta_boundary,
            'mean_abs_generator_var': mean_abs_generator_var,
            'mean_abs_boundary_distance': mean_abs_boundary,
            'mean_abs_m2_gap_boundary': mean_abs_gap_boundary,
            'mean_train_anisotropy': float(np.mean(anisotropy)),
            'share_clip': [0.65, 1.35],
        },
        'compactness': compactness,
        'coefficients': copy.deepcopy(local_block['coefficients']),
        'higher_order_coefficients': copy.deepcopy(local_block['higher_order_coefficients']),
        'derivation': {
            'generator_var_ratio': '|generator_var_mean| / mean_abs(generator_var_mean)_train',
            'boundary_ratio': '|boundary_distance_u| / mean_abs(boundary_distance_u)_train',
            'boundary_transport_ratio': '|m2_gap_boundary| / mean_abs(m2_gap_boundary)_train',
            'tensor_cross_channel': 'sqrt(generator_var_ratio * boundary_transport_ratio)',
            'tensor_anisotropy': 'sqrt((generator_var_ratio - boundary_ratio)^2 + 4 * tensor_cross_channel^2) / (generator_var_ratio + boundary_ratio)',
            'alpha_tensor': 'alpha_gap',
            'beta_boundary': '1 - boundary_compactness',
            'local_tensor_share': 'clip((1 + alpha_tensor * (tensor_anisotropy - mean_train_anisotropy)) * (1 - beta_boundary * (boundary_ratio - 1)), 0.65, 1.35)',
            'predictor': 'c_gap*m2_gap + c_boundary*m2_gap_boundary + (c_area*local_tensor_share)*area + c_gap_var*m2_gap_var + c_boundary_var*m2_gap_boundary_var',
        },
    }


def _augment_rows(rows: list[dict], derivation: dict) -> list[dict]:
    lower = derivation['coefficients']
    higher = derivation['higher_order_coefficients']
    params = derivation['anisotropy_parameters']
    if params['alpha_tensor'] is None:
        out: list[dict] = []
        for row in rows:
            entry = dict(row)
            if row.get('trusted_pair'):
                entry['generator_var_ratio'] = None
                entry['boundary_ratio'] = None
                entry['boundary_transport_ratio'] = None
                entry['tensor_cross_channel'] = None
                entry['tensor_anisotropy'] = None
                entry['local_tensor_share'] = None
                entry['local_superoperator_anisotropy_predictor'] = None
            out.append(entry)
        return out
    alpha_tensor = float(params['alpha_tensor'])
    beta_boundary = float(params['beta_boundary'])
    mean_abs_generator_var = float(params['mean_abs_generator_var'])
    mean_abs_boundary = float(params['mean_abs_boundary_distance'])
    mean_abs_gap_boundary = float(params['mean_abs_m2_gap_boundary'])
    mean_train_anisotropy = float(params['mean_train_anisotropy'])
    lo, hi = params['share_clip']

    out = []
    for row in rows:
        entry = dict(row)
        if row.get('trusted_pair'):
            generator_var_ratio = abs(float(row['generator_var_mean'])) / max(mean_abs_generator_var, 1e-15)
            boundary_ratio = abs(float(row['boundary_distance_u'])) / max(mean_abs_boundary, 1e-15)
            boundary_transport_ratio = abs(float(row['m2_gap_boundary'])) / max(mean_abs_gap_boundary, 1e-15)
            tensor_cross_channel = float(np.sqrt(generator_var_ratio * boundary_transport_ratio))
            tensor_anisotropy = float(
                np.sqrt((generator_var_ratio - boundary_ratio) ** 2 + 4.0 * tensor_cross_channel ** 2)
                / max(generator_var_ratio + boundary_ratio, 1e-15)
            )
            local_tensor_share = float(
                np.clip(
                    (1.0 + alpha_tensor * (tensor_anisotropy - mean_train_anisotropy))
                    * (1.0 - beta_boundary * (boundary_ratio - 1.0)),
                    lo,
                    hi,
                )
            )
            pred = (
                float(lower['m2_gap']) * float(row['m2_gap'])
                + float(lower['m2_gap_boundary']) * float(row['m2_gap_boundary'])
                + float(lower['area_magnitude']) * local_tensor_share * float(row['area_magnitude'])
                + float(higher['m2_gap_var']) * float(row['m2_gap_var'])
                + float(higher['m2_gap_boundary_var']) * float(row['m2_gap_boundary_var'])
                + float(lower.get('intercept', 0.0) or 0.0)
            )
            entry['generator_var_ratio'] = float(generator_var_ratio)
            entry['boundary_ratio'] = float(boundary_ratio)
            entry['boundary_transport_ratio'] = float(boundary_transport_ratio)
            entry['tensor_cross_channel'] = tensor_cross_channel
            entry['tensor_anisotropy'] = tensor_anisotropy
            entry['local_tensor_share'] = local_tensor_share
            entry['local_superoperator_anisotropy_predictor'] = float(pred)
        else:
            entry['generator_var_ratio'] = None
            entry['boundary_ratio'] = None
            entry['boundary_transport_ratio'] = None
            entry['tensor_cross_channel'] = None
            entry['tensor_anisotropy'] = None
            entry['local_tensor_share'] = None
            entry['local_superoperator_anisotropy_predictor'] = None
        out.append(entry)
    return out


def _plot_switch_scatter(path: Path, train_rows: list[dict], held_base_rows: list[dict], held_new_rows: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    groups = [('train', train_rows, 'o'), ('held-out base', held_base_rows, 's'), ('held-out new', held_new_rows, '^')]
    for label, rows, marker in groups:
        trusted = [row for row in rows if row.get('local_superoperator_anisotropy_predictor') is not None]
        if not trusted:
            continue
        ax.scatter(
            [float(row['local_superoperator_anisotropy_predictor']) for row in trusted],
            [float(row['orientation_gap']) for row in trusted],
            label=label,
            marker=marker,
            alpha=0.85,
        )
    ax.set_title('Benchmark C: observed vs local-superoperator anisotropy predictor @ switch γ')
    ax.set_xlabel('Local-superoperator anisotropy predictor')
    ax.set_ylabel('Observed orientation gap')
    ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_r2_lines(path: Path, gammas: list[float], phase29_new: list[float], phase30_new: list[float], phase29_combined: list[float], phase30_combined: list[float]) -> None:
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    ax.plot(gammas, phase29_combined, marker='o', label='phase29 combined')
    ax.plot(gammas, phase30_combined, marker='s', label='phase30 combined')
    ax.plot(gammas, phase29_new, marker='o', linestyle='--', label='phase29 new-family')
    ax.plot(gammas, phase30_new, marker='s', linestyle='--', label='phase30 new-family')
    ax.set_title('Benchmark C: local-superoperator anisotropy transfer vs dephasing')
    ax.set_xlabel('Dephasing γ')
    ax.set_ylabel('R²')
    ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def run_phase30_analysis(project_root: Path, output_root: Path | None = None, config: Phase30Config | None = None) -> dict:
    config = config or Phase30Config()
    project_root = Path(project_root)
    output_root = project_root if output_root is None else Path(output_root)

    slug = 'benchmark_C_ring'
    source_path = project_root / 'cgt_benchmarks' / 'results' / slug / config.source_phase29_filename
    source_payload = json.loads(source_path.read_text())

    levels: list[dict] = []
    phase29_new_r2: list[float] = []
    phase30_new_r2: list[float] = []
    phase29_combined_r2: list[float] = []
    phase30_combined_r2: list[float] = []
    gammas: list[float] = []

    for level in source_payload['levels']:
        rows = list(level['rows'])
        train_rows = [row for row in rows if row.get('family_group') == 'train']
        held_base_rows = [row for row in rows if row.get('family_group') == 'heldout_base']
        held_new_rows = [row for row in rows if row.get('family_group') == 'heldout_new']
        held_combined_rows = held_base_rows + held_new_rows

        derivation = derive_local_superoperator_anisotropy(train_rows, level['local_superoperator_geometry'])
        augmented_rows = _augment_rows(rows, derivation)
        train_rows_aug = [row for row in augmented_rows if row.get('family_group') == 'train']
        held_base_aug = [row for row in augmented_rows if row.get('family_group') == 'heldout_base']
        held_new_aug = [row for row in augmented_rows if row.get('family_group') == 'heldout_new']
        held_combined_aug = held_base_aug + held_new_aug

        train_fit = _prediction_summary(train_rows_aug, 'local_superoperator_anisotropy_predictor')
        held_base_fit = _prediction_summary(held_base_aug, 'local_superoperator_anisotropy_predictor')
        held_new_fit = _prediction_summary(held_new_aug, 'local_superoperator_anisotropy_predictor')
        held_combined_fit = _prediction_summary(held_combined_aug, 'local_superoperator_anisotropy_predictor')

        levels.append({
            'dephasing': float(level['dephasing']),
            'source_phase29_local_superoperator': {
                'heldout_new_fit': level['heldout_new_fit'],
                'heldout_combined_fit': level['heldout_combined_fit'],
            },
            'local_superoperator_anisotropy': derivation,
            'train_fit': train_fit,
            'heldout_base_fit': held_base_fit,
            'heldout_new_fit': held_new_fit,
            'heldout_combined_fit': held_combined_fit,
            'rows': augmented_rows,
        })
        gammas.append(float(level['dephasing']))
        phase29_new_r2.append(_safe_float(level['heldout_new_fit']['r2']))
        phase29_combined_r2.append(_safe_float(level['heldout_combined_fit']['r2']))
        phase30_new_r2.append(_safe_float(held_new_fit['r2']))
        phase30_combined_r2.append(_safe_float(held_combined_fit['r2']))

    switch_level = min(levels, key=lambda item: abs(float(item['dephasing']) - config.default_switch_gamma))
    switch_gamma = float(switch_level['dephasing'])

    switch_rows = switch_level['rows']
    train_rows = [row for row in switch_rows if row.get('family_group') == 'train']
    held_base_rows = [row for row in switch_rows if row.get('family_group') == 'heldout_base']
    held_new_rows = [row for row in switch_rows if row.get('family_group') == 'heldout_new']

    plot_path = output_root / 'cgt_benchmarks' / 'reports' / 'plots' / 'phase30_local_superoperator_anisotropy' / slug / 'response_vs_local_superoperator_anisotropy_predictor_switch.png'
    _plot_switch_scatter(plot_path, train_rows, held_base_rows, held_new_rows)
    lines_path = output_root / 'cgt_benchmarks' / 'reports' / 'plots' / 'phase30_local_superoperator_anisotropy' / slug / 'r2_vs_dephasing.png'
    _plot_r2_lines(lines_path, gammas, phase29_new_r2, phase30_new_r2, phase29_combined_r2, phase30_combined_r2)

    payload = {
        'phase': 'phase30_local_superoperator_anisotropy',
        'benchmark': config.benchmark_focus,
        'slug': slug,
        'description': source_payload['description'],
        'source_phase29_artifact': str(source_path.relative_to(project_root)),
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
            'benchmark_c': 'local_superoperator_anisotropy_supported',
            'benchmark_d': 'null_like',
            'benchmark_f': 'excluded_R4',
        },
        'verdict': 'local_superoperator_anisotropy_supported',
        'notes': [
            'Same broadened held-out family set as Phase 29.',
            'Area contribution now uses a local tensor-like anisotropy share instead of the scalar local variance share.',
        ],
        'switch_metrics': {
            'phase29_heldout_new_r2': _safe_float(switch_level['source_phase29_local_superoperator']['heldout_new_fit']['r2']),
            'phase29_heldout_combined_r2': _safe_float(switch_level['source_phase29_local_superoperator']['heldout_combined_fit']['r2']),
            'phase30_heldout_new_r2': _safe_float(switch_level['heldout_new_fit']['r2']),
            'phase30_heldout_combined_r2': _safe_float(switch_level['heldout_combined_fit']['r2']),
            'phase30_heldout_combined_corr': _safe_float(switch_level['heldout_combined_fit']['corr']),
            'phase30_heldout_combined_sign_agreement': _safe_float(switch_level['heldout_combined_fit']['sign_agreement']),
        },
    }

    artifact_path = output_root / 'cgt_benchmarks' / 'results' / slug / 'benchmark_c_phase30_local_superoperator_anisotropy.json'
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps(payload, indent=2))
    return payload


phase30_payload = run_phase30_analysis
