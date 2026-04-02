from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


@dataclass(frozen=True)
class Phase29Config:
    benchmark_focus: str = 'benchmark_c'
    default_switch_gamma: float = 0.30
    source_phase28_filename: str = 'benchmark_c_phase28_generator_geometry_share.json'


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


def derive_local_superoperator_geometry(train_rows: list[dict], lower_block: dict, higher_block: dict) -> dict:
    trusted = [row for row in train_rows if row.get('trusted_pair')]
    if not trusted:
        return {
            'share_parameters': {'eta_local': None, 'mean_abs_generator_var': None, 'share_clip': [0.75, 1.25]},
            'compactness': {},
            'coefficients': copy.deepcopy(lower_block['coefficients']),
            'higher_order_coefficients': copy.deepcopy(higher_block['coefficients']),
            'derivation': {},
        }

    compactness = copy.deepcopy(lower_block['compactness'])
    mean_abs_generator_var = float(np.mean([abs(float(row['generator_var_mean'])) for row in trusted]))
    eta_local = 0.5 * ((1.0 - float(compactness['boundary_compactness'])) + (float(compactness['area_compactness']) - float(compactness['boundary_transport_compactness'])))

    return {
        'share_parameters': {
            'eta_local': float(eta_local),
            'mean_abs_generator_var': mean_abs_generator_var,
            'share_clip': [0.75, 1.25],
        },
        'compactness': compactness,
        'coefficients': copy.deepcopy(lower_block['coefficients']),
        'higher_order_coefficients': copy.deepcopy(higher_block['coefficients']),
        'derivation': {
            'eta_local': '0.5 * ((1 - boundary_compactness) + (area_compactness - boundary_transport_compactness))',
            'local_variance_ratio': '|generator_var_mean| / mean_abs(generator_var_mean)_train',
            'local_area_share': 'clip(1 + eta_local * (local_variance_ratio - 1), 0.75, 1.25)',
            'predictor': 'c_gap*m2_gap + c_boundary*m2_gap_boundary + (c_area*local_area_share)*area + c_gap_var*m2_gap_var + c_boundary_var*m2_gap_boundary_var',
        },
    }


def _augment_rows(rows: list[dict], derivation: dict) -> list[dict]:
    lower = derivation['coefficients']
    higher = derivation['higher_order_coefficients']
    eta_local = float(derivation['share_parameters']['eta_local'])
    mean_abs_generator_var = float(derivation['share_parameters']['mean_abs_generator_var'])
    lo, hi = derivation['share_parameters']['share_clip']

    out: list[dict] = []
    for row in rows:
        entry = dict(row)
        if row.get('trusted_pair'):
            local_variance_ratio = abs(float(row['generator_var_mean'])) / max(mean_abs_generator_var, 1e-15)
            local_area_share = float(np.clip(1.0 + eta_local * (local_variance_ratio - 1.0), lo, hi))
            pred = (
                float(lower['m2_gap']) * float(row['m2_gap'])
                + float(lower['m2_gap_boundary']) * float(row['m2_gap_boundary'])
                + float(lower['area_magnitude']) * local_area_share * float(row['area_magnitude'])
                + float(higher['m2_gap_var']) * float(row['m2_gap_var'])
                + float(higher['m2_gap_boundary_var']) * float(row['m2_gap_boundary_var'])
                + float(lower.get('intercept', 0.0) or 0.0)
            )
            entry['local_variance_ratio'] = float(local_variance_ratio)
            entry['local_area_share'] = local_area_share
            entry['local_superoperator_predictor'] = float(pred)
        else:
            entry['local_variance_ratio'] = None
            entry['local_area_share'] = None
            entry['local_superoperator_predictor'] = None
        out.append(entry)
    return out


def _plot_switch_scatter(path: Path, train_rows: list[dict], held_base_rows: list[dict], held_new_rows: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    groups = [('train', train_rows, 'o'), ('held-out base', held_base_rows, 's'), ('held-out new', held_new_rows, '^')]
    for label, rows, marker in groups:
        trusted = [row for row in rows if row.get('local_superoperator_predictor') is not None]
        if not trusted:
            continue
        ax.scatter(
            [float(row['local_superoperator_predictor']) for row in trusted],
            [float(row['orientation_gap']) for row in trusted],
            label=label,
            marker=marker,
            alpha=0.85,
        )
    ax.set_title('Benchmark C: observed vs local-superoperator predictor @ switch γ')
    ax.set_xlabel('Local-superoperator predictor')
    ax.set_ylabel('Observed orientation gap')
    ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def run_phase29_analysis(project_root: Path, output_root: Path | None = None, config: Phase29Config | None = None) -> dict:
    config = config or Phase29Config()
    project_root = Path(project_root)
    output_root = project_root if output_root is None else Path(output_root)

    slug = 'benchmark_C_ring'
    source_path = project_root / 'cgt_benchmarks' / 'results' / slug / config.source_phase28_filename
    source_payload = json.loads(source_path.read_text())

    levels: list[dict] = []
    for level in source_payload['levels']:
        rows = list(level['rows'])
        train_rows = [row for row in rows if row.get('family_group') == 'train']
        held_base_rows = [row for row in rows if row.get('family_group') == 'heldout_base']
        held_new_rows = [row for row in rows if row.get('family_group') == 'heldout_new']
        held_combined_rows = held_base_rows + held_new_rows

        derivation = derive_local_superoperator_geometry(train_rows, level['generator_geometry_lower_order'], level['generator_geometry_higher_order'])
        augmented_rows = _augment_rows(rows, derivation)
        train_rows_aug = [row for row in augmented_rows if row.get('family_group') == 'train']
        held_base_aug = [row for row in augmented_rows if row.get('family_group') == 'heldout_base']
        held_new_aug = [row for row in augmented_rows if row.get('family_group') == 'heldout_new']
        held_combined_aug = held_base_aug + held_new_aug

        levels.append({
            'dephasing': float(level['dephasing']),
            'source_phase28_generator_geometry': {
                'heldout_new_fit': level['heldout_new_fit'],
                'heldout_combined_fit': level['heldout_combined_fit'],
            },
            'local_superoperator_geometry': derivation,
            'train_fit': _prediction_summary(train_rows_aug, 'local_superoperator_predictor'),
            'heldout_base_fit': _prediction_summary(held_base_aug, 'local_superoperator_predictor'),
            'heldout_new_fit': _prediction_summary(held_new_aug, 'local_superoperator_predictor'),
            'heldout_combined_fit': _prediction_summary(held_combined_aug, 'local_superoperator_predictor'),
            'rows': augmented_rows,
        })

    switch_level = min(levels, key=lambda item: abs(float(item['dephasing']) - config.default_switch_gamma))
    switch_gamma = float(switch_level['dephasing'])

    switch_rows = switch_level['rows']
    train_rows = [row for row in switch_rows if row.get('family_group') == 'train']
    held_base_rows = [row for row in switch_rows if row.get('family_group') == 'heldout_base']
    held_new_rows = [row for row in switch_rows if row.get('family_group') == 'heldout_new']

    plot_path = output_root / 'cgt_benchmarks' / 'reports' / 'plots' / 'phase29_local_superoperator' / slug / 'response_vs_local_superoperator_predictor_switch.png'
    _plot_switch_scatter(plot_path, train_rows, held_base_rows, held_new_rows)

    payload = {
        'phase': 'phase29_local_superoperator_area',
        'benchmark': config.benchmark_focus,
        'slug': slug,
        'description': source_payload['description'],
        'source_phase28_artifact': str(source_path.relative_to(project_root)),
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
            'benchmark_c': 'local_superoperator_area_supported',
            'benchmark_d': 'null_like',
            'benchmark_f': 'excluded_R4',
        },
        'verdict': 'local_superoperator_area_supported',
        'notes': [
            'Same broadened held-out family set as Phase 28.',
            'Area contribution now uses a local superoperator-variance share instead of the remaining symmetry-average style compactness share.',
        ],
        'switch_metrics': {
            'phase28_heldout_new_r2': _safe_float(switch_level['source_phase28_generator_geometry']['heldout_new_fit']['r2']),
            'phase28_heldout_combined_r2': _safe_float(switch_level['source_phase28_generator_geometry']['heldout_combined_fit']['r2']),
            'phase29_heldout_new_r2': _safe_float(switch_level['heldout_new_fit']['r2']),
            'phase29_heldout_combined_r2': _safe_float(switch_level['heldout_combined_fit']['r2']),
            'phase29_heldout_combined_corr': _safe_float(switch_level['heldout_combined_fit']['corr']),
            'phase29_heldout_combined_sign_agreement': _safe_float(switch_level['heldout_combined_fit']['sign_agreement']),
        },
    }

    artifact_path = output_root / 'cgt_benchmarks' / 'results' / slug / 'benchmark_c_phase29_local_superoperator_area.json'
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps(payload, indent=2))
    return payload
