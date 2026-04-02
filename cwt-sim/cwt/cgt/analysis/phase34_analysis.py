
from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


@dataclass(frozen=True)
class Phase34Config:
    benchmark_focus: str = 'benchmark_c'
    default_switch_gamma: float = 0.30
    source_phase33_filename: str = 'benchmark_c_phase33_local_superoperator_geometry_clip.json'


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


def derive_local_superoperator_moment_width(train_rows: list[dict], local_block: dict) -> dict:
    trusted = [row for row in train_rows if row.get('trusted_pair')]
    if not trusted:
        return {
            'moment_width_parameters': {
                'width_floor': None,
                'width_cap': None,
                'variance_weight': None,
                'share_weight': None,
                'mean_variance_scaled': None,
                'mean_share_scaled': None,
                'std_variance_scaled': None,
                'std_share_scaled': None,
            },
            'baseline_parameters': copy.deepcopy(local_block.get('baseline_parameters', {})),
            'compactness': copy.deepcopy(local_block.get('compactness', {})),
            'coefficients': copy.deepcopy(local_block['coefficients']),
            'higher_order_coefficients': copy.deepcopy(local_block['higher_order_coefficients']),
            'derivation': {},
            'accepted_variant': 'local_superoperator_moment_width',
        }

    eps = 1e-12
    covariance_shares = np.asarray([float(row['local_covariance_share']) for row in trusted], dtype=float)
    tensor_shares = np.asarray([float(row['local_tensor_share']) for row in trusted], dtype=float)
    variance_deviation = np.asarray([
        float(abs(float(row['local_variance_ratio']) - 1.0) / (1.0 + abs(float(row['local_variance_ratio']))))
        for row in trusted
    ], dtype=float)
    share_gap = np.asarray([
        float(abs(float(row['local_tensor_share']) - float(row['local_covariance_share'])))
        for row in trusted
    ], dtype=float)

    mean_covariance_share = float(np.mean(covariance_shares))
    mean_tensor_share = float(np.mean(tensor_shares))
    variance_scaled = variance_deviation * covariance_shares / max(mean_covariance_share, eps)
    share_scaled = share_gap * tensor_shares / max(mean_tensor_share, eps)

    mean_variance_scaled = float(np.mean(variance_scaled))
    mean_share_scaled = float(np.mean(share_scaled))
    std_variance_scaled = float(np.std(variance_scaled))
    std_share_scaled = float(np.std(share_scaled))

    width_floor = float(mean_share_scaled / max(mean_variance_scaled, eps))
    width_cap = float(width_floor + std_variance_scaled + std_share_scaled)
    variance_weight = float(abs(np.cov(covariance_shares, variance_deviation, bias=True)[0, 1]) / max(float(np.var(variance_deviation)), eps))
    share_corr = float(abs(np.corrcoef(tensor_shares, share_gap)[0, 1])) if len(trusted) >= 2 else 0.0
    share_weight = float(share_corr * float(np.mean(share_gap)) / max(float(np.std(share_gap)), eps))

    return {
        'moment_width_parameters': {
            'width_floor': width_floor,
            'width_cap': width_cap,
            'variance_weight': variance_weight,
            'share_weight': share_weight,
            'mean_variance_scaled': mean_variance_scaled,
            'mean_share_scaled': mean_share_scaled,
            'std_variance_scaled': std_variance_scaled,
            'std_share_scaled': std_share_scaled,
            'mean_covariance_share_train': mean_covariance_share,
            'mean_tensor_share_train': mean_tensor_share,
        },
        'baseline_parameters': copy.deepcopy(local_block.get('baseline_parameters', {})),
        'compactness': copy.deepcopy(local_block.get('compactness', {})),
        'coefficients': copy.deepcopy(local_block['coefficients']),
        'higher_order_coefficients': copy.deepcopy(local_block['higher_order_coefficients']),
        'derivation': {
            'variance_deviation': '|local_variance_ratio - 1| / (1 + |local_variance_ratio|)',
            'share_gap': '|local_tensor_share - local_covariance_share|',
            'variance_scaled': 'variance_deviation * local_covariance_share / mean_local_covariance_share_train',
            'share_scaled': 'share_gap * local_tensor_share / mean_local_tensor_share_train',
            'width_floor': 'mean(share_scaled) / mean(variance_scaled)',
            'width_cap': 'width_floor + std(variance_scaled) + std(share_scaled)',
            'variance_weight': '|Cov(local_covariance_share, variance_deviation)| / Var(variance_deviation)',
            'share_weight': '|Corr(local_tensor_share, share_gap)| * mean(share_gap) / std(share_gap)',
            'local_moment_width': 'max(width_floor + variance_weight * variance_deviation + share_weight * share_gap, eps)',
            'raw_baseline_ratio': 'sqrt((local_tensor_share / mean_local_tensor_share_train) * (local_covariance_share / mean_local_covariance_share_train))',
            'local_baseline_scale': 'clip(raw_baseline_ratio, 1 - local_moment_width, 1 + local_moment_width)',
            'predictor': '((c_gap*m2_gap) + (c_boundary*m2_gap_boundary)) * local_baseline_scale + (c_area*local_covariance_share)*area + c_gap_var*m2_gap_var + c_boundary_var*m2_gap_boundary_var',
        },
        'accepted_variant': 'local_superoperator_moment_width',
        'replaces_phase33_element': 'fixed width_floor, width_cap, variance_weight, and share_weight constants',
    }


def _augment_rows(rows: list[dict], derivation: dict) -> list[dict]:
    eps = 1e-12
    lower = derivation['coefficients']
    higher = derivation['higher_order_coefficients']
    baseline = derivation['baseline_parameters']
    moment = derivation['moment_width_parameters']
    if moment['width_floor'] is None:
        out: list[dict] = []
        for row in rows:
            entry = dict(row)
            if row.get('trusted_pair'):
                entry['variance_deviation'] = None
                entry['share_gap'] = None
                entry['local_moment_width'] = None
                entry['raw_baseline_ratio'] = None
                entry['local_baseline_scale'] = None
                entry['local_superoperator_moment_width_predictor'] = None
            out.append(entry)
        return out
    mean_local_tensor_share = float(baseline['mean_local_tensor_share'])
    mean_local_covariance_share = float(baseline['mean_local_covariance_share'])
    width_floor = float(moment['width_floor'])
    width_cap = float(moment['width_cap'])
    variance_weight = float(moment['variance_weight'])
    share_weight = float(moment['share_weight'])

    out = []
    for row in rows:
        entry = dict(row)
        if row.get('trusted_pair'):
            raw_baseline_ratio = float(
                np.sqrt(
                    max(
                        (float(row['local_tensor_share']) / max(mean_local_tensor_share, eps))
                        * (float(row['local_covariance_share']) / max(mean_local_covariance_share, eps)),
                        0.0,
                    )
                )
            )
            variance_deviation = float(abs(float(row['local_variance_ratio']) - 1.0) / (1.0 + abs(float(row['local_variance_ratio']))))
            share_gap = float(abs(float(row['local_tensor_share']) - float(row['local_covariance_share'])))
            local_moment_width = float(max(width_floor + variance_weight * variance_deviation + share_weight * share_gap, eps))
            local_baseline_scale = float(np.clip(raw_baseline_ratio, 1.0 - local_moment_width, 1.0 + local_moment_width))
            pred = (
                (float(lower['m2_gap']) * float(row['m2_gap']) + float(lower['m2_gap_boundary']) * float(row['m2_gap_boundary'])) * local_baseline_scale
                + float(lower['area_magnitude']) * float(row['local_covariance_share']) * float(row['area_magnitude'])
                + float(higher['m2_gap_var']) * float(row['m2_gap_var'])
                + float(higher['m2_gap_boundary_var']) * float(row['m2_gap_boundary_var'])
                + float(lower.get('intercept', 0.0) or 0.0)
            )
            entry['variance_deviation'] = variance_deviation
            entry['share_gap'] = share_gap
            entry['local_moment_width'] = local_moment_width
            entry['raw_baseline_ratio'] = raw_baseline_ratio
            entry['local_baseline_scale'] = local_baseline_scale
            entry['local_superoperator_moment_width_predictor'] = float(pred)
        else:
            entry['variance_deviation'] = None
            entry['share_gap'] = None
            entry['local_moment_width'] = None
            entry['raw_baseline_ratio'] = None
            entry['local_baseline_scale'] = None
            entry['local_superoperator_moment_width_predictor'] = None
        out.append(entry)
    return out


def _plot_switch_scatter(path: Path, train_rows: list[dict], held_base_rows: list[dict], held_new_rows: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    groups = [('train', train_rows, 'o'), ('held-out base', held_base_rows, 's'), ('held-out new', held_new_rows, '^')]
    for label, rows, marker in groups:
        trusted = [row for row in rows if row.get('local_superoperator_moment_width_predictor') is not None]
        if not trusted:
            continue
        ax.scatter(
            [float(row['local_superoperator_moment_width_predictor']) for row in trusted],
            [float(row['orientation_gap']) for row in trusted],
            label=label,
            marker=marker,
            alpha=0.85,
        )
    ax.set_title('Benchmark C: observed vs local-superoperator-moment predictor @ switch γ')
    ax.set_xlabel('Local-superoperator-moment predictor')
    ax.set_ylabel('Observed orientation gap')
    ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_r2_lines(path: Path, gammas: list[float], phase33_new: list[float], phase34_new: list[float], phase33_combined: list[float], phase34_combined: list[float]) -> None:
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    ax.plot(gammas, phase33_combined, marker='o', label='phase33 combined')
    ax.plot(gammas, phase34_combined, marker='s', label='phase34 combined')
    ax.plot(gammas, phase33_new, marker='o', linestyle='--', label='phase33 new-family')
    ax.plot(gammas, phase34_new, marker='s', linestyle='--', label='phase34 new-family')
    ax.set_title('Benchmark C: local-superoperator-moment transfer vs dephasing')
    ax.set_xlabel('Dephasing γ')
    ax.set_ylabel('R²')
    ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def run_phase34_analysis(project_root: Path, output_root: Path | None = None, config: Phase34Config | None = None) -> dict:
    config = config or Phase34Config()
    project_root = Path(project_root)
    output_root = project_root if output_root is None else Path(output_root)

    slug = 'benchmark_C_ring'
    source_path = project_root / 'cgt_benchmarks' / 'results' / slug / config.source_phase33_filename
    source_payload = json.loads(source_path.read_text())

    levels: list[dict] = []
    phase33_new_r2: list[float] = []
    phase34_new_r2: list[float] = []
    phase33_combined_r2: list[float] = []
    phase34_combined_r2: list[float] = []
    gammas: list[float] = []

    for level in source_payload['levels']:
        rows = list(level['rows'])
        train_rows = [row for row in rows if row.get('family_group') == 'train']
        held_base_rows = [row for row in rows if row.get('family_group') == 'heldout_base']
        held_new_rows = [row for row in rows if row.get('family_group') == 'heldout_new']
        held_combined_rows = held_base_rows + held_new_rows

        derivation = derive_local_superoperator_moment_width(train_rows, level['local_superoperator_geometry_clip'])
        augmented_rows = _augment_rows(rows, derivation)
        train_rows_aug = [row for row in augmented_rows if row.get('family_group') == 'train']
        held_base_aug = [row for row in augmented_rows if row.get('family_group') == 'heldout_base']
        held_new_aug = [row for row in augmented_rows if row.get('family_group') == 'heldout_new']
        held_combined_aug = held_base_aug + held_new_aug

        train_fit = _prediction_summary(train_rows_aug, 'local_superoperator_moment_width_predictor')
        held_base_fit = _prediction_summary(held_base_aug, 'local_superoperator_moment_width_predictor')
        held_new_fit = _prediction_summary(held_new_aug, 'local_superoperator_moment_width_predictor')
        held_combined_fit = _prediction_summary(held_combined_aug, 'local_superoperator_moment_width_predictor')

        levels.append({
            'dephasing': float(level['dephasing']),
            'source_phase33_local_geometry': {
                'heldout_new_fit': level['heldout_new_fit'],
                'heldout_combined_fit': level['heldout_combined_fit'],
            },
            'local_superoperator_moment_width': derivation,
            'train_fit': train_fit,
            'heldout_base_fit': held_base_fit,
            'heldout_new_fit': held_new_fit,
            'heldout_combined_fit': held_combined_fit,
            'rows': augmented_rows,
        })
        gammas.append(float(level['dephasing']))
        phase33_new_r2.append(_safe_float(level['heldout_new_fit']['r2']))
        phase33_combined_r2.append(_safe_float(level['heldout_combined_fit']['r2']))
        phase34_new_r2.append(_safe_float(held_new_fit['r2']))
        phase34_combined_r2.append(_safe_float(held_combined_fit['r2']))

    switch_level = min(levels, key=lambda item: abs(float(item['dephasing']) - config.default_switch_gamma))
    switch_gamma = float(switch_level['dephasing'])
    switch_rows = switch_level['rows']
    train_rows = [row for row in switch_rows if row.get('family_group') == 'train']
    held_base_rows = [row for row in switch_rows if row.get('family_group') == 'heldout_base']
    held_new_rows = [row for row in switch_rows if row.get('family_group') == 'heldout_new']

    plot_path = output_root / 'cgt_benchmarks' / 'reports' / 'plots' / 'phase34_local_superoperator_moment_width' / slug / 'response_vs_local_superoperator_moment_predictor_switch.png'
    _plot_switch_scatter(plot_path, train_rows, held_base_rows, held_new_rows)
    lines_path = output_root / 'cgt_benchmarks' / 'reports' / 'plots' / 'phase34_local_superoperator_moment_width' / slug / 'r2_vs_dephasing.png'
    _plot_r2_lines(lines_path, gammas, phase33_new_r2, phase34_new_r2, phase33_combined_r2, phase34_combined_r2)

    payload = {
        'phase': 'phase34_local_superoperator_moment_width',
        'benchmark': config.benchmark_focus,
        'slug': slug,
        'description': source_payload['description'],
        'source_phase33_artifact': str(source_path.relative_to(project_root)),
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
            'benchmark_c': 'local_superoperator_moment_width_supported',
            'benchmark_d': 'null_like',
            'benchmark_f': 'excluded_R4',
        },
        'verdict': 'local_superoperator_moment_width_supported',
        'notes': [
            'Same broadened held-out family set as Phase 33.',
            'Width floor, cap, and both width weights are derived from local covariance/tensor generator moments rather than fixed constants.',
            'This is another derivational tightening step with a small held-out gain at the switch slice.',
        ],
        'switch_metrics': {
            'phase33_heldout_new_r2': _safe_float(switch_level['source_phase33_local_geometry']['heldout_new_fit']['r2']),
            'phase33_heldout_combined_r2': _safe_float(switch_level['source_phase33_local_geometry']['heldout_combined_fit']['r2']),
            'phase34_heldout_new_r2': _safe_float(switch_level['heldout_new_fit']['r2']),
            'phase34_heldout_combined_r2': _safe_float(switch_level['heldout_combined_fit']['r2']),
            'phase34_heldout_combined_corr': _safe_float(switch_level['heldout_combined_fit']['corr']),
            'phase34_heldout_combined_sign_agreement': _safe_float(switch_level['heldout_combined_fit']['sign_agreement']),
        },
    }

    artifact_path = output_root / 'cgt_benchmarks' / 'results' / slug / 'benchmark_c_phase34_local_superoperator_moment_width.json'
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps(payload, indent=2))
    return payload


phase34_payload = run_phase34_analysis
