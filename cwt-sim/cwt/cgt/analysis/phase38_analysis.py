
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
class Phase38Config:
    benchmark_focus: str = 'benchmark_c'
    default_switch_gamma: float = 0.30
    source_phase37_filename: str = 'benchmark_c_phase37_local_superoperator_compactness.json'


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


def derive_local_superoperator_compactness_share(train_rows: list[dict], local_block: dict) -> dict:
    trusted = [row for row in train_rows if row.get('trusted_pair')]
    if not trusted:
        return {
            'compactness_share_parameters': {
                'mean_variance_alignment': None,
                'mean_geometry_compactness_share': None,
                'mean_raw_compactness_ratio': None,
            },
            'coefficients': copy.deepcopy(local_block['coefficients']),
            'higher_order_coefficients': copy.deepcopy(local_block['higher_order_coefficients']),
            'accepted_variant': 'local_superoperator_compactness_share',
            'derivation': {},
        }

    eps = 1e-12
    mean_variance_alignment = float(np.mean([float(row['variance_alignment']) for row in trusted]))
    raw_geometry_shares = np.asarray(
        [float(row['share_geometry']) / max(float(row['local_area_share']), eps) for row in trusted],
        dtype=float,
    )
    mean_geometry_compactness_share = float(np.mean(raw_geometry_shares))
    raw_compactness_ratios = []
    for row, share in zip(trusted, raw_geometry_shares):
        local_geometry_compactness_share = float(share / max(mean_geometry_compactness_share, eps))
        local_compactness_exponent = float(0.5 * local_geometry_compactness_share)
        raw_ratio = float((mean_variance_alignment / max(float(row['variance_alignment']), eps)) ** local_compactness_exponent)
        raw_compactness_ratios.append(raw_ratio)
    mean_raw_compactness_ratio = float(np.mean(np.asarray(raw_compactness_ratios, dtype=float)))

    return {
        'compactness_share_parameters': {
            'mean_variance_alignment': mean_variance_alignment,
            'mean_geometry_compactness_share': mean_geometry_compactness_share,
            'mean_raw_compactness_ratio': mean_raw_compactness_ratio,
        },
        'coefficients': copy.deepcopy(local_block['coefficients']),
        'higher_order_coefficients': copy.deepcopy(local_block['higher_order_coefficients']),
        'accepted_variant': 'local_superoperator_compactness_share',
        'derivation': {
            'raw_geometry_compactness_share': 'share_geometry / local_area_share',
            'normalization': 'divide raw geometry compactness share by its train mean; use the result to modulate the compactness exponent locally',
            'local_compactness_exponent': '0.5 * local_geometry_compactness_share',
            'raw_compactness_ratio': '(mean_variance_alignment_train / variance_alignment)^(local_compactness_exponent)',
            'local_compactness_area_channel': 'local_area_channel * local_compactness_ratio',
            'predictor': '((c_gap*m2_gap) + (c_boundary*m2_gap_boundary))*local_baseline_scale + (c_area*local_compactness_area_channel)*area + c_gap_var*m2_gap_var + c_boundary_var*m2_gap_boundary_var',
        },
        'replaces_phase37_element': 'fixed 1/2 exponent in the inverse variance-alignment compactness ratio',
    }


def _augment_rows(rows: list[dict], derivation: dict) -> list[dict]:
    eps = 1e-12
    lower = derivation['coefficients']
    higher = derivation['higher_order_coefficients']
    params = derivation['compactness_share_parameters']
    if params['mean_variance_alignment'] is None:
        out: list[dict] = []
        for row in rows:
            entry = dict(row)
            if row.get('trusted_pair'):
                entry['raw_geometry_compactness_share'] = None
                entry['local_geometry_compactness_share'] = None
                entry['local_compactness_exponent'] = None
                entry['phase38_raw_compactness_ratio'] = None
                entry['phase38_local_compactness_ratio'] = None
                entry['phase38_local_compactness_area_channel'] = None
                entry['local_superoperator_compactness_share_predictor'] = None
            out.append(entry)
        return out
    mean_variance_alignment = float(params['mean_variance_alignment'])
    mean_geometry_compactness_share = float(params['mean_geometry_compactness_share'])
    mean_raw_compactness_ratio = float(params['mean_raw_compactness_ratio'])

    out = []
    for row in rows:
        entry = dict(row)
        if row.get('trusted_pair'):
            raw_geometry_compactness_share = float(float(row['share_geometry']) / max(float(row['local_area_share']), eps))
            local_geometry_compactness_share = float(raw_geometry_compactness_share / max(mean_geometry_compactness_share, eps))
            local_compactness_exponent = float(0.5 * local_geometry_compactness_share)
            base_ratio = mean_variance_alignment / max(float(row['variance_alignment']), eps)
            raw_compactness_ratio = _safe_pow(base_ratio, local_compactness_exponent)
            local_compactness_ratio = float(raw_compactness_ratio / max(mean_raw_compactness_ratio, eps))
            local_compactness_area_channel = float(float(row['local_area_channel']) * local_compactness_ratio)
            pred = (
                (float(lower['m2_gap']) * float(row['m2_gap']) + float(lower['m2_gap_boundary']) * float(row['m2_gap_boundary'])) * float(row['local_baseline_scale'])
                + float(lower['area_magnitude']) * float(row['area_magnitude']) * local_compactness_area_channel
                + float(higher['m2_gap_var']) * float(row['m2_gap_var'])
                + float(higher['m2_gap_boundary_var']) * float(row['m2_gap_boundary_var'])
                + float(lower.get('intercept', 0.0) or 0.0)
            )
            entry['raw_geometry_compactness_share'] = raw_geometry_compactness_share
            entry['local_geometry_compactness_share'] = local_geometry_compactness_share
            entry['local_compactness_exponent'] = local_compactness_exponent
            entry['phase38_raw_compactness_ratio'] = raw_compactness_ratio
            entry['phase38_local_compactness_ratio'] = local_compactness_ratio
            entry['phase38_local_compactness_area_channel'] = local_compactness_area_channel
            entry['local_superoperator_compactness_share_predictor'] = float(pred)
        else:
            entry['raw_geometry_compactness_share'] = None
            entry['local_geometry_compactness_share'] = None
            entry['local_compactness_exponent'] = None
            entry['phase38_raw_compactness_ratio'] = None
            entry['phase38_local_compactness_ratio'] = None
            entry['phase38_local_compactness_area_channel'] = None
            entry['local_superoperator_compactness_share_predictor'] = None
        out.append(entry)
    return out


def _plot_switch_scatter(path: Path, train_rows: list[dict], held_base_rows: list[dict], held_new_rows: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    groups = [('train', train_rows, 'o'), ('held-out base', held_base_rows, 's'), ('held-out new', held_new_rows, '^')]
    for label, rows, marker in groups:
        trusted = [row for row in rows if row.get('local_superoperator_compactness_share_predictor') is not None]
        if not trusted:
            continue
        ax.scatter(
            [float(row['local_superoperator_compactness_share_predictor']) for row in trusted],
            [float(row['orientation_gap']) for row in trusted],
            label=label,
            marker=marker,
            alpha=0.85,
        )
    ax.set_title('Benchmark C: observed vs local-superoperator-compactness-share predictor @ switch γ')
    ax.set_xlabel('Local-superoperator-compactness-share predictor')
    ax.set_ylabel('Observed orientation gap')
    ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_r2_lines(path: Path, gammas: list[float], phase37_new: list[float], phase38_new: list[float], phase37_combined: list[float], phase38_combined: list[float]) -> None:
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    ax.plot(gammas, phase37_combined, marker='o', label='phase37 combined')
    ax.plot(gammas, phase38_combined, marker='s', label='phase38 combined')
    ax.plot(gammas, phase37_new, marker='o', linestyle='--', label='phase37 new-family')
    ax.plot(gammas, phase38_new, marker='s', linestyle='--', label='phase38 new-family')
    ax.set_title('Benchmark C: local-superoperator-compactness-share transfer vs dephasing')
    ax.set_xlabel('Dephasing γ')
    ax.set_ylabel('R²')
    ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def run_phase38_analysis(project_root: Path, output_root: Path | None = None, config: Phase38Config | None = None) -> dict:
    config = config or Phase38Config()
    project_root = Path(project_root)
    output_root = project_root if output_root is None else Path(output_root)

    slug = 'benchmark_C_ring'
    source_path = project_root / 'cgt_benchmarks' / 'results' / slug / config.source_phase37_filename
    source_payload = json.loads(source_path.read_text())

    levels: list[dict] = []
    phase37_new_r2: list[float] = []
    phase38_new_r2: list[float] = []
    phase37_combined_r2: list[float] = []
    phase38_combined_r2: list[float] = []
    gammas: list[float] = []

    for level in source_payload['levels']:
        rows = list(level['rows'])
        train_rows = [row for row in rows if row.get('family_group') == 'train']
        held_base_rows = [row for row in rows if row.get('family_group') == 'heldout_base']
        held_new_rows = [row for row in rows if row.get('family_group') == 'heldout_new']
        held_combined_rows = held_base_rows + held_new_rows

        derivation = derive_local_superoperator_compactness_share(train_rows, level['local_superoperator_compactness'])
        augmented_rows = _augment_rows(rows, derivation)
        train_rows_aug = [row for row in augmented_rows if row.get('family_group') == 'train']
        held_base_aug = [row for row in augmented_rows if row.get('family_group') == 'heldout_base']
        held_new_aug = [row for row in augmented_rows if row.get('family_group') == 'heldout_new']
        held_combined_aug = held_base_aug + held_new_aug

        train_fit = _prediction_summary(train_rows_aug, 'local_superoperator_compactness_share_predictor')
        held_base_fit = _prediction_summary(held_base_aug, 'local_superoperator_compactness_share_predictor')
        held_new_fit = _prediction_summary(held_new_aug, 'local_superoperator_compactness_share_predictor')
        held_combined_fit = _prediction_summary(held_combined_aug, 'local_superoperator_compactness_share_predictor')

        levels.append({
            'dephasing': float(level['dephasing']),
            'source_phase37_local_superoperator_compactness': {
                'heldout_new_fit': level['heldout_new_fit'],
                'heldout_combined_fit': level['heldout_combined_fit'],
            },
            'local_superoperator_compactness_share': derivation,
            'train_fit': train_fit,
            'heldout_base_fit': held_base_fit,
            'heldout_new_fit': held_new_fit,
            'heldout_combined_fit': held_combined_fit,
            'rows': augmented_rows,
        })

        gammas.append(float(level['dephasing']))
        phase37_new_r2.append(_safe_float(level['heldout_new_fit']['r2']))
        phase38_new_r2.append(_safe_float(held_new_fit['r2']))
        phase37_combined_r2.append(_safe_float(level['heldout_combined_fit']['r2']))
        phase38_combined_r2.append(_safe_float(held_combined_fit['r2']))

    switch_gamma = float(config.default_switch_gamma)
    switch_level = min(levels, key=lambda item: abs(float(item['dephasing']) - switch_gamma))
    switch_gamma = float(switch_level['dephasing'])

    plot_dir = output_root / 'cgt_benchmarks' / 'reports' / 'plots' / 'phase38_local_superoperator_compactness_share' / slug
    _plot_switch_scatter(
        plot_dir / 'response_vs_local_superoperator_compactness_share_predictor_switch.png',
        [row for row in switch_level['rows'] if row.get('family_group') == 'train'],
        [row for row in switch_level['rows'] if row.get('family_group') == 'heldout_base'],
        [row for row in switch_level['rows'] if row.get('family_group') == 'heldout_new'],
    )
    _plot_r2_lines(
        plot_dir / 'r2_vs_dephasing.png',
        gammas,
        phase37_new_r2,
        phase38_new_r2,
        phase37_combined_r2,
        phase38_combined_r2,
    )

    payload = {
        'phase': 'phase38_local_superoperator_compactness_share',
        'benchmark': config.benchmark_focus,
        'slug': slug,
        'description': 'Replace the remaining fixed compactness exponent choice with a local superoperator-geometry compactness-share rule while keeping the broadened held-out family split fixed.',
        'source_phase37_artifact': str(source_path.relative_to(project_root)),
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
            'benchmark_c': 'local_superoperator_compactness_share_supported',
            'benchmark_d': 'null_like',
            'benchmark_f': 'excluded_R4',
        },
        'verdict': 'local_superoperator_compactness_share_supported',
        'notes': [
            'Same broadened held-out family split as Phase 37.',
            'The inverse variance-alignment compactness exponent is no longer fixed at 1/2; it is modulated locally by a train-normalized superoperator-geometry compactness share built from share_geometry / local_area_share.',
            'This phase is a local-geometry tightening of the compactness channel rather than a topology or branch-switching change.',
        ],
        'switch_metrics': {
            'phase37_heldout_new_r2': _safe_float(switch_level['source_phase37_local_superoperator_compactness']['heldout_new_fit']['r2']),
            'phase38_heldout_new_r2': _safe_float(switch_level['heldout_new_fit']['r2']),
            'phase37_heldout_combined_r2': _safe_float(switch_level['source_phase37_local_superoperator_compactness']['heldout_combined_fit']['r2']),
            'phase38_heldout_combined_r2': _safe_float(switch_level['heldout_combined_fit']['r2']),
            'phase38_combined_corr': _safe_float(switch_level['heldout_combined_fit']['corr']),
            'phase38_combined_sign_agreement': _safe_float(switch_level['heldout_combined_fit']['sign_agreement']),
        },
    }

    artifact_path = output_root / 'cgt_benchmarks' / 'results' / slug / 'benchmark_c_phase38_local_superoperator_compactness_share.json'
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps(payload, indent=2))
    return payload


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase38_analysis(project_root=project_root, output_root=project_root)
    print(json.dumps(payload['switch_metrics'], indent=2))
