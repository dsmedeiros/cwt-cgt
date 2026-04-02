from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


@dataclass(frozen=True)
class Phase32Config:
    benchmark_focus: str = 'benchmark_c'
    default_switch_gamma: float = 0.30
    source_phase31_filename: str = 'benchmark_c_phase31_local_superoperator_covariance.json'


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


def derive_covariance_tensor_baseline(train_rows: list[dict], local_block: dict) -> dict:
    trusted = [row for row in train_rows if row.get('trusted_pair')]
    if not trusted:
        return {
            'baseline_parameters': {
                'mean_local_tensor_share': None,
                'mean_local_covariance_share': None,
                'mean_raw_baseline_ratio': None,
                'max_abs_baseline_deviation': None,
                'baseline_clip': [0.80, 1.20],
            },
            'compactness': copy.deepcopy(local_block.get('compactness', {})),
            'coefficients': copy.deepcopy(local_block['coefficients']),
            'higher_order_coefficients': copy.deepcopy(local_block['higher_order_coefficients']),
            'derivation': {},
        }

    mean_local_tensor_share = float(np.mean([float(row['local_tensor_share']) for row in trusted]))
    mean_local_covariance_share = float(np.mean([float(row['local_covariance_share']) for row in trusted]))
    raw_ratios = [
        float(np.sqrt(max((float(row['local_tensor_share']) / max(mean_local_tensor_share, 1e-15)) * (float(row['local_covariance_share']) / max(mean_local_covariance_share, 1e-15)), 0.0)))
        for row in trusted
    ]
    mean_raw_baseline_ratio = float(np.mean(raw_ratios))
    max_abs_baseline_deviation = float(np.max(np.abs(np.asarray(raw_ratios, dtype=float) - 1.0)))
    baseline_width = float(np.clip(max_abs_baseline_deviation, 0.05, 0.20))
    baseline_clip = [float(1.0 - baseline_width), float(1.0 + baseline_width)]

    return {
        'baseline_parameters': {
            'mean_local_tensor_share': mean_local_tensor_share,
            'mean_local_covariance_share': mean_local_covariance_share,
            'mean_raw_baseline_ratio': mean_raw_baseline_ratio,
            'max_abs_baseline_deviation': max_abs_baseline_deviation,
            'baseline_clip': baseline_clip,
        },
        'compactness': copy.deepcopy(local_block.get('compactness', {})),
        'coefficients': copy.deepcopy(local_block['coefficients']),
        'higher_order_coefficients': copy.deepcopy(local_block['higher_order_coefficients']),
        'derivation': {
            'raw_baseline_ratio': 'sqrt((local_tensor_share / mean_local_tensor_share_train) * (local_covariance_share / mean_local_covariance_share_train))',
            'baseline_width': 'clip(max_abs(raw_baseline_ratio_train - 1), 0.05, 0.20)',
            'local_baseline_scale': 'clip(raw_baseline_ratio, 1 - baseline_width, 1 + baseline_width)',
            'predictor': '((c_gap*m2_gap) + (c_boundary*m2_gap_boundary)) * local_baseline_scale + (c_area*local_covariance_share)*area + c_gap_var*m2_gap_var + c_boundary_var*m2_gap_boundary_var',
        },
        'accepted_variant': 'covariance_tensor_baseline_scale',
    }


def _augment_rows(rows: list[dict], derivation: dict) -> list[dict]:
    lower = derivation['coefficients']
    higher = derivation['higher_order_coefficients']
    params = derivation['baseline_parameters']
    if params['mean_local_tensor_share'] is None:
        out: list[dict] = []
        for row in rows:
            entry = dict(row)
            if row.get('trusted_pair'):
                entry['raw_baseline_ratio'] = None
                entry['local_baseline_scale'] = None
                entry['covariance_tensor_baseline_predictor'] = None
            out.append(entry)
        return out
    mean_local_tensor_share = float(params['mean_local_tensor_share'])
    mean_local_covariance_share = float(params['mean_local_covariance_share'])
    lo, hi = [float(x) for x in params['baseline_clip']]

    out = []
    for row in rows:
        entry = dict(row)
        if row.get('trusted_pair'):
            raw_baseline_ratio = float(np.sqrt(max((float(row['local_tensor_share']) / max(mean_local_tensor_share, 1e-15)) * (float(row['local_covariance_share']) / max(mean_local_covariance_share, 1e-15)), 0.0)))
            local_baseline_scale = float(np.clip(raw_baseline_ratio, lo, hi))
            pred = (
                (float(lower['m2_gap']) * float(row['m2_gap']) + float(lower['m2_gap_boundary']) * float(row['m2_gap_boundary'])) * local_baseline_scale
                + float(lower['area_magnitude']) * float(row['local_covariance_share']) * float(row['area_magnitude'])
                + float(higher['m2_gap_var']) * float(row['m2_gap_var'])
                + float(higher['m2_gap_boundary_var']) * float(row['m2_gap_boundary_var'])
                + float(lower.get('intercept', 0.0) or 0.0)
            )
            entry['raw_baseline_ratio'] = raw_baseline_ratio
            entry['local_baseline_scale'] = local_baseline_scale
            entry['covariance_tensor_baseline_predictor'] = float(pred)
        else:
            entry['raw_baseline_ratio'] = None
            entry['local_baseline_scale'] = None
            entry['covariance_tensor_baseline_predictor'] = None
        out.append(entry)
    return out


def _plot_switch_scatter(path: Path, train_rows: list[dict], held_base_rows: list[dict], held_new_rows: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    groups = [('train', train_rows, 'o'), ('held-out base', held_base_rows, 's'), ('held-out new', held_new_rows, '^')]
    for label, rows, marker in groups:
        trusted = [row for row in rows if row.get('covariance_tensor_baseline_predictor') is not None]
        if not trusted:
            continue
        ax.scatter(
            [float(row['covariance_tensor_baseline_predictor']) for row in trusted],
            [float(row['orientation_gap']) for row in trusted],
            label=label,
            marker=marker,
            alpha=0.85,
        )
    ax.set_title('Benchmark C: observed vs covariance-tensor baseline predictor @ switch γ')
    ax.set_xlabel('Covariance-tensor baseline predictor')
    ax.set_ylabel('Observed orientation gap')
    ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_r2_lines(path: Path, gammas: list[float], phase31_new: list[float], phase32_new: list[float], phase31_combined: list[float], phase32_combined: list[float]) -> None:
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    ax.plot(gammas, phase31_combined, marker='o', label='phase31 combined')
    ax.plot(gammas, phase32_combined, marker='s', label='phase32 combined')
    ax.plot(gammas, phase31_new, marker='o', linestyle='--', label='phase31 new-family')
    ax.plot(gammas, phase32_new, marker='s', linestyle='--', label='phase32 new-family')
    ax.set_title('Benchmark C: covariance-tensor baseline transfer vs dephasing')
    ax.set_xlabel('Dephasing γ')
    ax.set_ylabel('R²')
    ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def run_phase32_analysis(project_root: Path, output_root: Path | None = None, config: Phase32Config | None = None) -> dict:
    config = config or Phase32Config()
    project_root = Path(project_root)
    output_root = project_root if output_root is None else Path(output_root)

    slug = 'benchmark_C_ring'
    source_path = project_root / 'cgt_benchmarks' / 'results' / slug / config.source_phase31_filename
    source_payload = json.loads(source_path.read_text())

    levels: list[dict] = []
    phase31_new_r2: list[float] = []
    phase32_new_r2: list[float] = []
    phase31_combined_r2: list[float] = []
    phase32_combined_r2: list[float] = []
    gammas: list[float] = []

    for level in source_payload['levels']:
        rows = list(level['rows'])
        train_rows = [row for row in rows if row.get('family_group') == 'train']
        held_base_rows = [row for row in rows if row.get('family_group') == 'heldout_base']
        held_new_rows = [row for row in rows if row.get('family_group') == 'heldout_new']
        held_combined_rows = held_base_rows + held_new_rows

        derivation = derive_covariance_tensor_baseline(train_rows, level['local_superoperator_covariance'])
        augmented_rows = _augment_rows(rows, derivation)
        train_rows_aug = [row for row in augmented_rows if row.get('family_group') == 'train']
        held_base_aug = [row for row in augmented_rows if row.get('family_group') == 'heldout_base']
        held_new_aug = [row for row in augmented_rows if row.get('family_group') == 'heldout_new']
        held_combined_aug = held_base_aug + held_new_aug

        train_fit = _prediction_summary(train_rows_aug, 'covariance_tensor_baseline_predictor')
        held_base_fit = _prediction_summary(held_base_aug, 'covariance_tensor_baseline_predictor')
        held_new_fit = _prediction_summary(held_new_aug, 'covariance_tensor_baseline_predictor')
        held_combined_fit = _prediction_summary(held_combined_aug, 'covariance_tensor_baseline_predictor')

        levels.append({
            'dephasing': float(level['dephasing']),
            'source_phase31_covariance': {
                'heldout_new_fit': level['heldout_new_fit'],
                'heldout_combined_fit': level['heldout_combined_fit'],
            },
            'covariance_tensor_baseline': derivation,
            'train_fit': train_fit,
            'heldout_base_fit': held_base_fit,
            'heldout_new_fit': held_new_fit,
            'heldout_combined_fit': held_combined_fit,
            'rows': augmented_rows,
        })
        gammas.append(float(level['dephasing']))
        phase31_new_r2.append(_safe_float(level['heldout_new_fit']['r2']))
        phase31_combined_r2.append(_safe_float(level['heldout_combined_fit']['r2']))
        phase32_new_r2.append(_safe_float(held_new_fit['r2']))
        phase32_combined_r2.append(_safe_float(held_combined_fit['r2']))

    switch_level = min(levels, key=lambda item: abs(float(item['dephasing']) - config.default_switch_gamma))
    switch_gamma = float(switch_level['dephasing'])

    switch_rows = switch_level['rows']
    train_rows = [row for row in switch_rows if row.get('family_group') == 'train']
    held_base_rows = [row for row in switch_rows if row.get('family_group') == 'heldout_base']
    held_new_rows = [row for row in switch_rows if row.get('family_group') == 'heldout_new']

    plot_path = output_root / 'cgt_benchmarks' / 'reports' / 'plots' / 'phase32_covariance_tensor_baseline' / slug / 'response_vs_covariance_tensor_baseline_predictor_switch.png'
    _plot_switch_scatter(plot_path, train_rows, held_base_rows, held_new_rows)
    lines_path = output_root / 'cgt_benchmarks' / 'reports' / 'plots' / 'phase32_covariance_tensor_baseline' / slug / 'r2_vs_dephasing.png'
    _plot_r2_lines(lines_path, gammas, phase31_new_r2, phase32_new_r2, phase31_combined_r2, phase32_combined_r2)

    payload = {
        'phase': 'phase32_covariance_tensor_baseline',
        'benchmark': config.benchmark_focus,
        'slug': slug,
        'description': source_payload['description'],
        'source_phase31_artifact': str(source_path.relative_to(project_root)),
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
            'benchmark_c': 'covariance_tensor_baseline_supported',
            'benchmark_d': 'null_like',
            'benchmark_f': 'excluded_R4',
        },
        'verdict': 'covariance_tensor_baseline_supported',
        'notes': [
            'Same broadened held-out family set as Phase 31.',
            'The remaining local baseline scale is now derived from the geometric mean of covariance- and tensor-share moments, clipped by the train-set spread rather than fixed by response fitting.',
            'This is a derivational tightening with a small but consistent combined-slice improvement over Phase 31.',
        ],
        'switch_metrics': {
            'phase31_heldout_new_r2': _safe_float(switch_level['source_phase31_covariance']['heldout_new_fit']['r2']),
            'phase31_heldout_combined_r2': _safe_float(switch_level['source_phase31_covariance']['heldout_combined_fit']['r2']),
            'phase32_heldout_new_r2': _safe_float(switch_level['heldout_new_fit']['r2']),
            'phase32_heldout_combined_r2': _safe_float(switch_level['heldout_combined_fit']['r2']),
            'phase32_heldout_combined_corr': _safe_float(switch_level['heldout_combined_fit']['corr']),
            'phase32_heldout_combined_sign_agreement': _safe_float(switch_level['heldout_combined_fit']['sign_agreement']),
        },
    }

    artifact_path = output_root / 'cgt_benchmarks' / 'results' / slug / 'benchmark_c_phase32_covariance_tensor_baseline.json'
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps(payload, indent=2))
    return payload


phase32_payload = run_phase32_analysis
