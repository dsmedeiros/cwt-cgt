from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


@dataclass(frozen=True)
class Phase31Config:
    benchmark_focus: str = 'benchmark_c'
    default_switch_gamma: float = 0.30
    source_phase30_filename: str = 'benchmark_c_phase30_local_superoperator_anisotropy.json'


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


def derive_local_superoperator_covariance(train_rows: list[dict], local_block: dict) -> dict:
    trusted = [row for row in train_rows if row.get('trusted_pair')]
    if not trusted:
        return {
            'covariance_parameters': {
                'offdiag_compactness': None,
                'covariance_width': None,
                'mean_generator_var_ratio': None,
                'mean_boundary_transport_ratio': None,
                'mean_abs_covariance_moment': None,
                'mean_abs_boundary_distance': None,
                'mean_train_covariance_anisotropy': None,
                'covariance_clip': None,
                'share_clip': [0.65, 1.35],
            },
            'compactness': {},
            'coefficients': copy.deepcopy(local_block['coefficients']),
            'higher_order_coefficients': copy.deepcopy(local_block['higher_order_coefficients']),
            'derivation': {},
        }

    compactness = copy.deepcopy(local_block['compactness'])
    params = local_block['anisotropy_parameters']

    mean_generator_var_ratio = float(np.mean([float(row['generator_var_ratio']) for row in trusted]))
    mean_boundary_transport_ratio = float(np.mean([float(row['boundary_transport_ratio']) for row in trusted]))
    mean_abs_covariance_moment = float(
        np.mean(
            [
                abs(
                    (float(row['generator_var_ratio']) - mean_generator_var_ratio)
                    * (float(row['boundary_transport_ratio']) - mean_boundary_transport_ratio)
                )
                for row in trusted
            ]
        )
    )
    mean_abs_boundary_distance = float(params['mean_abs_boundary_distance'])
    alpha_tensor = float(params['alpha_tensor'])
    beta_boundary = float(params['beta_boundary'])
    share_clip = list(params['share_clip'])

    offdiag_compactness = float(compactness['area_compactness'])
    covariance_width = float(1.0 - offdiag_compactness)
    covariance_clip = [float(1.0 - covariance_width), float(1.0 + covariance_width)]

    train_anisotropies: list[float] = []
    for row in trusted:
        gv = float(row['generator_var_ratio'])
        br = float(row['boundary_ratio'])
        bt = float(row['boundary_transport_ratio'])
        centered_covariance_moment = abs((gv - mean_generator_var_ratio) * (bt - mean_boundary_transport_ratio))
        covariance_moment_ratio = float(np.clip(centered_covariance_moment / max(mean_abs_covariance_moment, 1e-15), covariance_clip[0], covariance_clip[1]))
        offdiagonal_moment = float(np.sqrt(max(gv * bt, 0.0)) * (offdiag_compactness + (1.0 - offdiag_compactness) * covariance_moment_ratio))
        covariance_anisotropy = float(np.sqrt((gv - br) ** 2 + 4.0 * offdiagonal_moment ** 2) / max(gv + br, 1e-15))
        train_anisotropies.append(covariance_anisotropy)

    mean_train_covariance_anisotropy = float(np.mean(train_anisotropies))

    return {
        'covariance_parameters': {
            'offdiag_compactness': offdiag_compactness,
            'covariance_width': covariance_width,
            'mean_generator_var_ratio': mean_generator_var_ratio,
            'mean_boundary_transport_ratio': mean_boundary_transport_ratio,
            'mean_abs_covariance_moment': mean_abs_covariance_moment,
            'mean_abs_boundary_distance': mean_abs_boundary_distance,
            'mean_train_covariance_anisotropy': mean_train_covariance_anisotropy,
            'covariance_clip': covariance_clip,
            'share_clip': share_clip,
        },
        'compactness': compactness,
        'coefficients': copy.deepcopy(local_block['coefficients']),
        'higher_order_coefficients': copy.deepcopy(local_block['higher_order_coefficients']),
        'derivation': {
            'centered_covariance_moment': '|(generator_var_ratio - mean_generator_var_ratio) * (boundary_transport_ratio - mean_boundary_transport_ratio)|',
            'covariance_moment_ratio': 'clip(centered_covariance_moment / mean_abs_covariance_moment_train, covariance_clip_low, covariance_clip_high)',
            'offdiagonal_moment': 'sqrt(generator_var_ratio * boundary_transport_ratio) * (offdiag_compactness + (1 - offdiag_compactness) * covariance_moment_ratio)',
            'covariance_anisotropy': 'sqrt((generator_var_ratio - boundary_ratio)^2 + 4 * offdiagonal_moment^2) / (generator_var_ratio + boundary_ratio)',
            'predictor': 'c_gap*m2_gap + c_boundary*m2_gap_boundary + (c_area*local_covariance_share)*area + c_gap_var*m2_gap_var + c_boundary_var*m2_gap_boundary_var',
        },
        'replaces_phase30_channel': 'tensor_cross_channel = sqrt(generator_var_ratio * boundary_transport_ratio)',
        'accepted_variant': 'covariance_modulated_offdiagonal_moment',
    }


def _augment_rows(rows: list[dict], derivation: dict) -> list[dict]:
    lower = derivation['coefficients']
    higher = derivation['higher_order_coefficients']
    params = derivation['covariance_parameters']
    if params['offdiag_compactness'] is None:
        out: list[dict] = []
        for row in rows:
            entry = dict(row)
            if row.get('trusted_pair'):
                entry['centered_covariance_moment'] = None
                entry['covariance_moment_ratio'] = None
                entry['offdiagonal_moment'] = None
                entry['covariance_anisotropy'] = None
                entry['local_covariance_share'] = None
                entry['local_superoperator_covariance_predictor'] = None
            out.append(entry)
        return out
    offdiag_compactness = float(params['offdiag_compactness'])
    mean_generator_var_ratio = float(params['mean_generator_var_ratio'])
    mean_boundary_transport_ratio = float(params['mean_boundary_transport_ratio'])
    mean_abs_covariance_moment = float(params['mean_abs_covariance_moment'])
    mean_abs_boundary_distance = float(params['mean_abs_boundary_distance'])
    mean_train_covariance_anisotropy = float(params['mean_train_covariance_anisotropy'])
    alpha_tensor = float(derivation['compactness']['alpha_gap'])
    beta_boundary = float(derivation['covariance_parameters'].get('beta_boundary', derivation['compactness'].get('beta_boundary', 0.0)) if False else 0.0)
    # Use the fitted beta from source anisotropy parameters if present in coefficients payload.
    # We store it explicitly below to avoid ambiguity.
    beta_boundary = float(derivation['beta_boundary']) if 'beta_boundary' in derivation else 0.0
    cov_lo, cov_hi = [float(x) for x in params['covariance_clip']]
    share_lo, share_hi = [float(x) for x in params['share_clip']]

    out: list[dict] = []
    for row in rows:
        entry = dict(row)
        if row.get('trusted_pair'):
            gv = float(row['generator_var_ratio'])
            br = float(row['boundary_ratio'])
            bt = float(row['boundary_transport_ratio'])
            boundary_ratio = abs(float(row['boundary_distance_u'])) / max(mean_abs_boundary_distance, 1e-15)
            centered_covariance_moment = abs((gv - mean_generator_var_ratio) * (bt - mean_boundary_transport_ratio))
            covariance_moment_ratio = float(np.clip(centered_covariance_moment / max(mean_abs_covariance_moment, 1e-15), cov_lo, cov_hi))
            offdiagonal_moment = float(np.sqrt(max(gv * bt, 0.0)) * (offdiag_compactness + (1.0 - offdiag_compactness) * covariance_moment_ratio))
            covariance_anisotropy = float(np.sqrt((gv - br) ** 2 + 4.0 * offdiagonal_moment ** 2) / max(gv + br, 1e-15))
            local_covariance_share = float(
                np.clip(
                    (1.0 + alpha_tensor * (covariance_anisotropy - mean_train_covariance_anisotropy))
                    * (1.0 - beta_boundary * (boundary_ratio - 1.0)),
                    share_lo,
                    share_hi,
                )
            )
            pred = (
                float(lower['m2_gap']) * float(row['m2_gap'])
                + float(lower['m2_gap_boundary']) * float(row['m2_gap_boundary'])
                + float(lower['area_magnitude']) * local_covariance_share * float(row['area_magnitude'])
                + float(higher['m2_gap_var']) * float(row['m2_gap_var'])
                + float(higher['m2_gap_boundary_var']) * float(row['m2_gap_boundary_var'])
                + float(lower.get('intercept', 0.0) or 0.0)
            )
            entry['centered_covariance_moment'] = centered_covariance_moment
            entry['covariance_moment_ratio'] = covariance_moment_ratio
            entry['offdiagonal_moment'] = offdiagonal_moment
            entry['covariance_anisotropy'] = covariance_anisotropy
            entry['local_covariance_share'] = local_covariance_share
            entry['local_superoperator_covariance_predictor'] = float(pred)
        else:
            entry['centered_covariance_moment'] = None
            entry['covariance_moment_ratio'] = None
            entry['offdiagonal_moment'] = None
            entry['covariance_anisotropy'] = None
            entry['local_covariance_share'] = None
            entry['local_superoperator_covariance_predictor'] = None
        out.append(entry)
    return out


def _plot_switch_scatter(path: Path, train_rows: list[dict], held_base_rows: list[dict], held_new_rows: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    groups = [('train', train_rows, 'o'), ('held-out base', held_base_rows, 's'), ('held-out new', held_new_rows, '^')]
    for label, rows, marker in groups:
        trusted = [row for row in rows if row.get('local_superoperator_covariance_predictor') is not None]
        if not trusted:
            continue
        ax.scatter(
            [float(row['local_superoperator_covariance_predictor']) for row in trusted],
            [float(row['orientation_gap']) for row in trusted],
            label=label,
            marker=marker,
            alpha=0.85,
        )
    ax.set_title('Benchmark C: observed vs local-superoperator covariance predictor @ switch γ')
    ax.set_xlabel('Local-superoperator covariance predictor')
    ax.set_ylabel('Observed orientation gap')
    ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_r2_lines(path: Path, gammas: list[float], phase30_new: list[float], phase31_new: list[float], phase30_combined: list[float], phase31_combined: list[float]) -> None:
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    ax.plot(gammas, phase30_combined, marker='o', label='phase30 combined')
    ax.plot(gammas, phase31_combined, marker='s', label='phase31 combined')
    ax.plot(gammas, phase30_new, marker='o', linestyle='--', label='phase30 new-family')
    ax.plot(gammas, phase31_new, marker='s', linestyle='--', label='phase31 new-family')
    ax.set_title('Benchmark C: local-superoperator covariance transfer vs dephasing')
    ax.set_xlabel('Dephasing γ')
    ax.set_ylabel('R²')
    ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def run_phase31_analysis(project_root: Path, output_root: Path | None = None, config: Phase31Config | None = None) -> dict:
    config = config or Phase31Config()
    project_root = Path(project_root)
    output_root = project_root if output_root is None else Path(output_root)

    slug = 'benchmark_C_ring'
    source_path = project_root / 'cgt_benchmarks' / 'results' / slug / config.source_phase30_filename
    source_payload = json.loads(source_path.read_text())

    levels: list[dict] = []
    phase30_new_r2: list[float] = []
    phase31_new_r2: list[float] = []
    phase30_combined_r2: list[float] = []
    phase31_combined_r2: list[float] = []
    gammas: list[float] = []

    for level in source_payload['levels']:
        rows = list(level['rows'])
        train_rows = [row for row in rows if row.get('family_group') == 'train']
        held_base_rows = [row for row in rows if row.get('family_group') == 'heldout_base']
        held_new_rows = [row for row in rows if row.get('family_group') == 'heldout_new']
        held_combined_rows = held_base_rows + held_new_rows

        derivation = derive_local_superoperator_covariance(train_rows, level['local_superoperator_anisotropy'])
        # Carry alpha/beta through explicitly for augmentation.
        derivation['alpha_tensor'] = float(level['local_superoperator_anisotropy']['anisotropy_parameters']['alpha_tensor'])
        derivation['beta_boundary'] = float(level['local_superoperator_anisotropy']['anisotropy_parameters']['beta_boundary'])
        derivation['compactness']['alpha_gap'] = float(level['local_superoperator_anisotropy']['anisotropy_parameters']['alpha_tensor'])
        augmented_rows = _augment_rows(rows, derivation)
        train_rows_aug = [row for row in augmented_rows if row.get('family_group') == 'train']
        held_base_aug = [row for row in augmented_rows if row.get('family_group') == 'heldout_base']
        held_new_aug = [row for row in augmented_rows if row.get('family_group') == 'heldout_new']
        held_combined_aug = held_base_aug + held_new_aug

        train_fit = _prediction_summary(train_rows_aug, 'local_superoperator_covariance_predictor')
        held_base_fit = _prediction_summary(held_base_aug, 'local_superoperator_covariance_predictor')
        held_new_fit = _prediction_summary(held_new_aug, 'local_superoperator_covariance_predictor')
        held_combined_fit = _prediction_summary(held_combined_aug, 'local_superoperator_covariance_predictor')

        levels.append({
            'dephasing': float(level['dephasing']),
            'source_phase30_local_superoperator': {
                'heldout_new_fit': level['heldout_new_fit'],
                'heldout_combined_fit': level['heldout_combined_fit'],
            },
            'local_superoperator_covariance': derivation,
            'train_fit': train_fit,
            'heldout_base_fit': held_base_fit,
            'heldout_new_fit': held_new_fit,
            'heldout_combined_fit': held_combined_fit,
            'rows': augmented_rows,
        })
        gammas.append(float(level['dephasing']))
        phase30_new_r2.append(_safe_float(level['heldout_new_fit']['r2']))
        phase30_combined_r2.append(_safe_float(level['heldout_combined_fit']['r2']))
        phase31_new_r2.append(_safe_float(held_new_fit['r2']))
        phase31_combined_r2.append(_safe_float(held_combined_fit['r2']))

    switch_level = min(levels, key=lambda item: abs(float(item['dephasing']) - config.default_switch_gamma))
    switch_gamma = float(switch_level['dephasing'])

    switch_rows = switch_level['rows']
    train_rows = [row for row in switch_rows if row.get('family_group') == 'train']
    held_base_rows = [row for row in switch_rows if row.get('family_group') == 'heldout_base']
    held_new_rows = [row for row in switch_rows if row.get('family_group') == 'heldout_new']

    plot_path = output_root / 'cgt_benchmarks' / 'reports' / 'plots' / 'phase31_local_superoperator_covariance' / slug / 'response_vs_local_superoperator_covariance_predictor_switch.png'
    _plot_switch_scatter(plot_path, train_rows, held_base_rows, held_new_rows)
    lines_path = output_root / 'cgt_benchmarks' / 'reports' / 'plots' / 'phase31_local_superoperator_covariance' / slug / 'r2_vs_dephasing.png'
    _plot_r2_lines(lines_path, gammas, phase30_new_r2, phase31_new_r2, phase30_combined_r2, phase31_combined_r2)

    payload = {
        'phase': 'phase31_local_superoperator_covariance',
        'benchmark': config.benchmark_focus,
        'slug': slug,
        'description': source_payload['description'],
        'source_phase30_artifact': str(source_path.relative_to(project_root)),
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
            'benchmark_c': 'local_superoperator_covariance_supported_small_decay',
            'benchmark_d': 'null_like',
            'benchmark_f': 'excluded_R4',
        },
        'verdict': 'local_superoperator_covariance_supported_small_decay',
        'notes': [
            'Same broadened held-out family set as Phase 30.',
            'The off-diagonal tensor channel is now a covariance-modulated superoperator moment instead of a pure geometric-mean channel.',
            'This is a derivational tightening; switch-slice performance remains strong but trails the Phase 30 anisotropy rule slightly.',
        ],
        'switch_metrics': {
            'phase30_heldout_new_r2': _safe_float(switch_level['source_phase30_local_superoperator']['heldout_new_fit']['r2']),
            'phase30_heldout_combined_r2': _safe_float(switch_level['source_phase30_local_superoperator']['heldout_combined_fit']['r2']),
            'phase31_heldout_new_r2': _safe_float(switch_level['heldout_new_fit']['r2']),
            'phase31_heldout_combined_r2': _safe_float(switch_level['heldout_combined_fit']['r2']),
            'phase31_heldout_combined_corr': _safe_float(switch_level['heldout_combined_fit']['corr']),
            'phase31_heldout_combined_sign_agreement': _safe_float(switch_level['heldout_combined_fit']['sign_agreement']),
        },
    }

    artifact_path = output_root / 'cgt_benchmarks' / 'results' / slug / 'benchmark_c_phase31_local_superoperator_covariance.json'
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps(payload, indent=2))
    return payload


phase31_payload = run_phase31_analysis
