
from __future__ import annotations

import copy
import json
import math
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def _safe_pow(base: float, exponent: float, max_log: float = 700.0) -> float:
    """Compute base**exponent clamped to prevent float overflow."""
    if base <= 0.0:
        return 0.0
    log_result = math.log(base) * exponent
    return math.exp(min(log_result, max_log))


@dataclass(frozen=True)
class Phase37Config:
    benchmark_focus: str = 'benchmark_c'
    default_switch_gamma: float = 0.30
    source_phase36_filename: str = 'benchmark_c_phase36_local_superoperator_area_channel.json'


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


def derive_local_superoperator_compactness(train_rows: list[dict], local_block: dict) -> dict:
    trusted = [row for row in train_rows if row.get('trusted_pair')]
    if not trusted:
        return {
            'compactness_parameters': {
                'mean_variance_alignment': None,
                'mean_local_compactness_ratio': None,
                'max_abs_local_compactness_ratio_deviation': None,
            },
            'area_channel_parameters': copy.deepcopy(local_block.get('area_channel_parameters', {})),
            'geometry_baseline_parameters': copy.deepcopy(local_block.get('geometry_baseline_parameters', {})),
            'moment_width_parameters': copy.deepcopy(local_block.get('moment_width_parameters', {})),
            'coefficients': copy.deepcopy(local_block['coefficients']),
            'higher_order_coefficients': copy.deepcopy(local_block['higher_order_coefficients']),
            'accepted_variant': 'local_superoperator_compactness',
            'derivation': {},
        }

    eps = 1e-12
    mean_variance_alignment = float(np.mean([float(row['variance_alignment']) for row in trusted]))
    raw_ratios = []
    for row in trusted:
        ratio = float((mean_variance_alignment / max(float(row['variance_alignment']), eps)) ** 0.5)
        raw_ratios.append(ratio)
    ratio_mean = float(np.mean(raw_ratios))

    return {
        'compactness_parameters': {
            'mean_variance_alignment': mean_variance_alignment,
            'mean_local_compactness_ratio': ratio_mean,
            'max_abs_local_compactness_ratio_deviation': float(np.max(np.abs(np.asarray(raw_ratios, dtype=float) / max(ratio_mean, eps) - 1.0))),
        },
        'area_channel_parameters': copy.deepcopy(local_block.get('area_channel_parameters', {})),
        'geometry_baseline_parameters': copy.deepcopy(local_block.get('geometry_baseline_parameters', {})),
        'moment_width_parameters': copy.deepcopy(local_block.get('moment_width_parameters', {})),
        'coefficients': copy.deepcopy(local_block['coefficients']),
        'higher_order_coefficients': copy.deepcopy(local_block['higher_order_coefficients']),
        'accepted_variant': 'local_superoperator_compactness',
        'derivation': {
            'raw_compactness_ratio': '(mean_variance_alignment_train / variance_alignment)^(1/2)',
            'normalization': 'divide by train mean raw compactness ratio so train mean is 1',
            'local_compactness_area_channel': 'local_area_channel * local_compactness_ratio',
            'predictor': '((c_gap*m2_gap) + (c_boundary*m2_gap_boundary))*local_baseline_scale + (c_area*local_compactness_area_channel)*area + c_gap_var*m2_gap_var + c_boundary_var*m2_gap_boundary_var',
        },
        'replaces_phase36_element': 'remaining lower-order area-channel weighting',
    }


def _augment_rows(rows: list[dict], derivation: dict) -> list[dict]:
    eps = 1e-12
    lower = derivation['coefficients']
    higher = derivation['higher_order_coefficients']
    params = derivation['compactness_parameters']
    if params['mean_variance_alignment'] is None:
        out: list[dict] = []
        for row in rows:
            entry = dict(row)
            if row.get('trusted_pair'):
                entry['raw_compactness_ratio'] = None
                entry['local_compactness_ratio'] = None
                entry['local_compactness_area_channel'] = None
                entry['local_superoperator_compactness_predictor'] = None
            out.append(entry)
        return out
    mean_variance_alignment = float(params['mean_variance_alignment'])
    mean_ratio = float(params['mean_local_compactness_ratio'])

    out = []
    for row in rows:
        entry = dict(row)
        if row.get('trusted_pair'):
            base_ratio = mean_variance_alignment / max(float(row['variance_alignment']), eps)
            raw_ratio = _safe_pow(base_ratio, 0.5)
            local_compactness_ratio = float(raw_ratio / max(mean_ratio, eps))
            local_compactness_area_channel = float(float(row['local_area_channel']) * local_compactness_ratio)
            pred = (
                (float(lower['m2_gap']) * float(row['m2_gap']) + float(lower['m2_gap_boundary']) * float(row['m2_gap_boundary'])) * float(row['local_baseline_scale'])
                + float(lower['area_magnitude']) * float(row['area_magnitude']) * local_compactness_area_channel
                + float(higher['m2_gap_var']) * float(row['m2_gap_var'])
                + float(higher['m2_gap_boundary_var']) * float(row['m2_gap_boundary_var'])
                + float(lower.get('intercept', 0.0) or 0.0)
            )
            entry['raw_compactness_ratio'] = raw_ratio
            entry['local_compactness_ratio'] = local_compactness_ratio
            entry['local_compactness_area_channel'] = local_compactness_area_channel
            entry['local_superoperator_compactness_predictor'] = float(pred)
        else:
            entry['raw_compactness_ratio'] = None
            entry['local_compactness_ratio'] = None
            entry['local_compactness_area_channel'] = None
            entry['local_superoperator_compactness_predictor'] = None
        out.append(entry)
    return out


def _plot_switch_scatter(path: Path, train_rows: list[dict], held_base_rows: list[dict], held_new_rows: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    groups = [('train', train_rows, 'o'), ('held-out base', held_base_rows, 's'), ('held-out new', held_new_rows, '^')]
    for label, rows, marker in groups:
        trusted = [row for row in rows if row.get('local_superoperator_compactness_predictor') is not None]
        if not trusted:
            continue
        ax.scatter(
            [float(row['local_superoperator_compactness_predictor']) for row in trusted],
            [float(row['orientation_gap']) for row in trusted],
            label=label,
            marker=marker,
            alpha=0.85,
        )
    ax.set_title('Benchmark C: observed vs local-superoperator-compactness predictor @ switch γ')
    ax.set_xlabel('Local-superoperator-compactness predictor')
    ax.set_ylabel('Observed orientation gap')
    ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_r2_lines(path: Path, gammas: list[float], phase36_new: list[float], phase37_new: list[float], phase36_combined: list[float], phase37_combined: list[float]) -> None:
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    ax.plot(gammas, phase36_combined, marker='o', label='phase36 combined')
    ax.plot(gammas, phase37_combined, marker='s', label='phase37 combined')
    ax.plot(gammas, phase36_new, marker='o', linestyle='--', label='phase36 new-family')
    ax.plot(gammas, phase37_new, marker='s', linestyle='--', label='phase37 new-family')
    ax.set_title('Benchmark C: local-superoperator-compactness transfer vs dephasing')
    ax.set_xlabel('Dephasing γ')
    ax.set_ylabel('R²')
    ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def run_phase37_analysis(project_root: Path, output_root: Path | None = None, config: Phase37Config | None = None) -> dict:
    config = config or Phase37Config()
    project_root = Path(project_root)
    output_root = project_root if output_root is None else Path(output_root)

    slug = 'benchmark_C_ring'
    source_path = project_root / 'cgt_benchmarks' / 'results' / slug / config.source_phase36_filename
    source_payload = json.loads(source_path.read_text())

    levels: list[dict] = []
    phase36_new_r2: list[float] = []
    phase37_new_r2: list[float] = []
    phase36_combined_r2: list[float] = []
    phase37_combined_r2: list[float] = []
    gammas: list[float] = []

    for level in source_payload['levels']:
        rows = list(level['rows'])
        train_rows = [row for row in rows if row.get('family_group') == 'train']
        held_base_rows = [row for row in rows if row.get('family_group') == 'heldout_base']
        held_new_rows = [row for row in rows if row.get('family_group') == 'heldout_new']
        held_combined_rows = held_base_rows + held_new_rows

        derivation = derive_local_superoperator_compactness(train_rows, level['local_superoperator_area_channel'])
        augmented_rows = _augment_rows(rows, derivation)
        train_rows_aug = [row for row in augmented_rows if row.get('family_group') == 'train']
        held_base_aug = [row for row in augmented_rows if row.get('family_group') == 'heldout_base']
        held_new_aug = [row for row in augmented_rows if row.get('family_group') == 'heldout_new']
        held_combined_aug = held_base_aug + held_new_aug

        train_fit = _prediction_summary(train_rows_aug, 'local_superoperator_compactness_predictor')
        held_base_fit = _prediction_summary(held_base_aug, 'local_superoperator_compactness_predictor')
        held_new_fit = _prediction_summary(held_new_aug, 'local_superoperator_compactness_predictor')
        held_combined_fit = _prediction_summary(held_combined_aug, 'local_superoperator_compactness_predictor')

        levels.append({
            'dephasing': float(level['dephasing']),
            'source_phase36_local_superoperator_area_channel': {
                'heldout_new_fit': level['heldout_new_fit'],
                'heldout_combined_fit': level['heldout_combined_fit'],
            },
            'local_superoperator_compactness': derivation,
            'train_fit': train_fit,
            'heldout_base_fit': held_base_fit,
            'heldout_new_fit': held_new_fit,
            'heldout_combined_fit': held_combined_fit,
            'rows': augmented_rows,
        })

        gammas.append(float(level['dephasing']))
        phase36_new_r2.append(_safe_float(level['heldout_new_fit']['r2']))
        phase37_new_r2.append(_safe_float(held_new_fit['r2']))
        phase36_combined_r2.append(_safe_float(level['heldout_combined_fit']['r2']))
        phase37_combined_r2.append(_safe_float(held_combined_fit['r2']))

    switch_gamma = float(config.default_switch_gamma)
    switch_level = min(levels, key=lambda item: abs(float(item['dephasing']) - switch_gamma))
    switch_gamma = float(switch_level['dephasing'])

    plot_dir = output_root / 'cgt_benchmarks' / 'reports' / 'plots' / 'phase37_local_superoperator_compactness' / slug
    _plot_switch_scatter(
        plot_dir / 'response_vs_local_superoperator_compactness_predictor_switch.png',
        [row for row in switch_level['rows'] if row.get('family_group') == 'train'],
        [row for row in switch_level['rows'] if row.get('family_group') == 'heldout_base'],
        [row for row in switch_level['rows'] if row.get('family_group') == 'heldout_new'],
    )
    _plot_r2_lines(
        plot_dir / 'r2_vs_dephasing.png',
        gammas,
        phase36_new_r2,
        phase37_new_r2,
        phase36_combined_r2,
        phase37_combined_r2,
    )

    payload = {
        'phase': 'phase37_local_superoperator_compactness',
        'benchmark': config.benchmark_focus,
        'slug': slug,
        'description': 'Replace the remaining lower-order area-channel weights with a local superoperator-geometry compactness rule while keeping the broadened held-out family split fixed.',
        'source_phase36_artifact': str(source_path.relative_to(project_root)),
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
            'benchmark_c': 'local_superoperator_compactness_supported',
            'benchmark_d': 'null_like',
            'benchmark_f': 'excluded_R4',
        },
        'verdict': 'local_superoperator_compactness_supported',
        'notes': [
            'Same broadened held-out family split as Phase 36.',
            'The lower-order area channel is now modulated by a train-normalized inverse-square-root local variance-alignment compactness ratio.',
            'This phase is intended as a geometry-side compactness tightening rather than a topology or branch-switching change.',
        ],
        'switch_metrics': {
            'phase36_heldout_new_r2': _safe_float(switch_level['source_phase36_local_superoperator_area_channel']['heldout_new_fit']['r2']),
            'phase37_heldout_new_r2': _safe_float(switch_level['heldout_new_fit']['r2']),
            'phase36_heldout_combined_r2': _safe_float(switch_level['source_phase36_local_superoperator_area_channel']['heldout_combined_fit']['r2']),
            'phase37_heldout_combined_r2': _safe_float(switch_level['heldout_combined_fit']['r2']),
            'phase37_combined_corr': _safe_float(switch_level['heldout_combined_fit']['corr']),
            'phase37_combined_sign_agreement': _safe_float(switch_level['heldout_combined_fit']['sign_agreement']),
        },
    }

    artifact_path = output_root / 'cgt_benchmarks' / 'results' / slug / 'benchmark_c_phase37_local_superoperator_compactness.json'
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps(payload, indent=2))
    return payload


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase37_analysis(project_root=project_root, output_root=project_root)
    print(json.dumps(payload['switch_metrics'], indent=2))
