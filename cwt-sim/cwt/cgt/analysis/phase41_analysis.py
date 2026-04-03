"""Phase 41 analysis: Pooled positive noisy scaffold rule across benchmarks C and G.

This module derives a single pooled positive-noisy scaffold rule from the
square/circle train rows of benchmarks C and G simultaneously, then evaluates
all held-out families on both benchmarks without any benchmark-specific refit.

Design intent
-------------
Phase 41 tests whether a rule derived jointly from two scaffold benchmarks
(C: standard ring topology, G: four-node skew ring topology) retains predictive
coherence when transferred back to both benchmarks' held-out families. The pooled
rule is fit once per dephasing level; no per-benchmark coefficient adjustment is
permitted.

Why this extends Phase 40
--------------------------
Phase 40 demonstrated that the Phase 39 rule (fit exclusively on benchmark C)
transfers to benchmark G's scaffold topology. Phase 41 goes further: rather than
just transferring a single-benchmark rule, it pools the training signal from both
topologies and derives one shared rule. If the pooled rule still achieves high R²
on both benchmarks' held-out families, this supports the scaffold-level
generalization hypothesis more strongly.

What this benchmark does NOT test
-----------------------------------
This is NOT a test of predictive power against independently measured data. It is
a consistency / portability scaffold: given the Phase 39/40 compactness-normalizer
structure, does pooling training signal across two scaffold topologies yield a rule
that degrades gracefully on held-out families of each topology? The R² values are
meaningful only in the relative sense (train vs held-out degradation), not as
absolute evidence of physical validity.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np

from cwt.cgt.analysis._utils import nan_to_none, safe_float, safe_pow


@dataclass(frozen=True)
class Phase41Config:
    default_switch_gamma: float = 0.30
    benchmark_c_slug: str = 'benchmark_C_ring'
    benchmark_g_slug: str = 'benchmark_G_skew_ring'
    benchmark_c_filename: str = 'benchmark_c_phase39_local_superoperator_compactness_normalizer.json'
    benchmark_g_filename: str = 'benchmark_g_phase40_second_positive_noisy.json'
    description: str = (
        'Derive one pooled positive-noisy scaffold rule from the square/circle train rows of '
        'benchmarks C and G, then evaluate held-out families on both benchmarks without '
        'benchmark-specific refit.'
    )


def _prediction_summary(rows: list[dict], key: str) -> dict:
    trusted = [row for row in rows if row.get('trusted_pair') and row.get(key) is not None]
    if not trusted:
        return {'r2': None, 'corr': None, 'count': 0, 'sign_agreement': None}
    y = np.asarray([float(row['orientation_gap']) for row in trusted], dtype=float)
    yhat = np.asarray([float(row[key]) for row in trusted], dtype=float)
    ss = float(np.dot(y - float(np.mean(y)), y - float(np.mean(y))))
    r2 = None if ss <= 1e-15 else float(1.0 - np.dot(y - yhat, y - yhat) / ss)
    corr = None
    if len(y) >= 2 and not (np.allclose(y, y[0]) or np.allclose(yhat, yhat[0])):
        corr = float(np.corrcoef(y, yhat)[0, 1])
    sign_agreement = float(np.mean(np.sign(y) == np.sign(yhat))) if len(y) else None
    return {'r2': r2, 'corr': corr, 'count': int(len(y)), 'sign_agreement': sign_agreement}


def _compute_phase39_channels(row: dict, mean_variance_alignment: float, mean_raw_compactness_ratio: float, exponent_scale: float) -> dict:
    eps = 1e-12
    local_area_share = float(row['local_area_share'])
    share_geometry = float(row['share_geometry'])
    local_tensor_share = float(row['local_tensor_share'])
    local_covariance_share = float(row['local_covariance_share'])
    variance_alignment = float(row['variance_alignment'])
    local_area_channel = float(row['local_area_channel'])

    raw_geometry_compactness_share = share_geometry / max(local_area_share, eps)
    local_compactness_normalizer = math.sqrt(max(local_tensor_share * local_covariance_share, eps)) / math.sqrt(max(local_area_share, eps))
    local_geometry_compactness_ratio = raw_geometry_compactness_share / max(local_compactness_normalizer, eps)
    local_compactness_exponent = exponent_scale * local_geometry_compactness_ratio
    raw_compactness_ratio = safe_pow(mean_variance_alignment / max(variance_alignment, eps), local_compactness_exponent)
    local_compactness_ratio = raw_compactness_ratio / max(mean_raw_compactness_ratio, eps)
    local_compactness_area_channel = local_area_channel * local_compactness_ratio
    return {
        'raw_geometry_compactness_share': raw_geometry_compactness_share,
        'local_compactness_normalizer': local_compactness_normalizer,
        'local_geometry_compactness_ratio': local_geometry_compactness_ratio,
        'local_compactness_exponent': local_compactness_exponent,
        'raw_compactness_ratio': raw_compactness_ratio,
        'local_compactness_ratio': local_compactness_ratio,
        'local_compactness_area_channel': local_compactness_area_channel,
    }


def _derive_pooled_rule(train_rows: list[dict], exponent_scale: float = 0.8) -> dict:
    trusted = [row for row in train_rows if row.get('trusted_pair')]
    if not trusted:
        raise ValueError('No trusted train rows available for pooled rule derivation.')

    mean_variance_alignment = float(np.mean([float(row['variance_alignment']) for row in trusted]))
    raw_ratios: list[float] = []
    for row in trusted:
        channels = _compute_phase39_channels(row, mean_variance_alignment, 1.0, exponent_scale)
        raw_ratios.append(float(channels['raw_compactness_ratio']))
    mean_raw_compactness_ratio = float(np.mean(raw_ratios))

    X: list[list[float]] = []
    y: list[float] = []
    for row in trusted:
        channels = _compute_phase39_channels(row, mean_variance_alignment, mean_raw_compactness_ratio, exponent_scale)
        X.append(
            [
                float(row['m2_gap']) * float(row['local_baseline_scale']),
                float(row['m2_gap_boundary']) * float(row['local_baseline_scale']),
                float(row['area_magnitude']) * float(channels['local_compactness_area_channel']),
                float(row['m2_gap_var']),
                float(row['m2_gap_boundary_var']),
                1.0,
            ]
        )
        y.append(float(row['orientation_gap']))
    beta = np.linalg.lstsq(np.asarray(X, dtype=float), np.asarray(y, dtype=float), rcond=None)[0]
    return {
        'compactness_normalizer_parameters': {
            'mean_variance_alignment': mean_variance_alignment,
            'mean_raw_compactness_ratio': mean_raw_compactness_ratio,
            'exponent_scale': exponent_scale,
        },
        'coefficients': {
            'm2_gap': float(beta[0]),
            'm2_gap_boundary': float(beta[1]),
            'area_magnitude': float(beta[2]),
            'intercept': float(beta[5]),
        },
        'higher_order_coefficients': {
            'm2_gap_var': float(beta[3]),
            'm2_gap_boundary_var': float(beta[4]),
        },
        'accepted_variant': 'pooled_positive_noisy_scaffold_rule',
        'train_benchmarks': ['benchmark_c', 'benchmark_g'],
        'derivation': {
            'train_rows': 'square/circle rows from benchmarks C and G pooled together',
            'feature_columns': [
                'm2_gap * local_baseline_scale',
                'm2_gap_boundary * local_baseline_scale',
                'area_magnitude * local_compactness_area_channel',
                'm2_gap_var',
                'm2_gap_boundary_var',
                'intercept',
            ],
        },
    }


def _augment_rows(rows: list[dict], rule: dict) -> list[dict]:
    params = rule['compactness_normalizer_parameters']
    coeff = rule['coefficients']
    higher = rule['higher_order_coefficients']
    out: list[dict] = []
    for row in rows:
        entry = dict(row)
        if row.get('trusted_pair'):
            channels = _compute_phase39_channels(
                row,
                float(params['mean_variance_alignment']),
                float(params['mean_raw_compactness_ratio']),
                float(params['exponent_scale']),
            )
            predictor = (
                (float(coeff['m2_gap']) * float(row['m2_gap']) + float(coeff['m2_gap_boundary']) * float(row['m2_gap_boundary'])) * float(row['local_baseline_scale'])
                + float(coeff['area_magnitude']) * float(row['area_magnitude']) * float(channels['local_compactness_area_channel'])
                + float(higher['m2_gap_var']) * float(row['m2_gap_var'])
                + float(higher['m2_gap_boundary_var']) * float(row['m2_gap_boundary_var'])
                + float(coeff.get('intercept', 0.0) or 0.0)
            )
            entry['pooled_positive_noisy_scaffold_predictor'] = float(predictor)
            entry.update({f'phase41_{k}': float(v) for k, v in channels.items()})
        else:
            entry['pooled_positive_noisy_scaffold_predictor'] = None
        out.append(entry)
    return out


def _group(rows: Iterable[dict], family_group: str | None = None) -> list[dict]:
    if family_group is None:
        return [row for row in rows if row.get('trusted_pair')]
    return [row for row in rows if row.get('trusted_pair') and row.get('family_group') == family_group]


def _plot_switch_scatter(path: Path, c_rows: list[dict], g_rows: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    groups = [
        ('benchmark C held-out', c_rows, 'o'),
        ('benchmark G held-out', g_rows, 's'),
    ]
    for label, rows, marker in groups:
        trusted = [r for r in rows if r.get('pooled_positive_noisy_scaffold_predictor') is not None]
        if not trusted:
            continue
        ax.scatter(
            [float(r['pooled_positive_noisy_scaffold_predictor']) for r in trusted],
            [float(r['orientation_gap']) for r in trusted],
            label=label,
            marker=marker,
            alpha=0.85,
        )
    ax.set_title('Pooled scaffold rule: observed vs predicted orientation gap @ switch \u03b3')
    ax.set_xlabel('Pooled scaffold predictor')
    ax.set_ylabel('Observed orientation gap')
    ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_r2_lines(path: Path, gammas: list[float], c_combined: list[float], g_combined: list[float], both_combined: list[float], both_new: list[float]) -> None:
    fig, ax = plt.subplots(figsize=(7.4, 4.8))
    ax.plot(gammas, c_combined, marker='o', label='benchmark C held-out combined')
    ax.plot(gammas, g_combined, marker='s', label='benchmark G held-out combined')
    ax.plot(gammas, both_combined, marker='d', label='pooled held-out combined')
    ax.plot(gammas, both_new, marker='^', linestyle='--', label='pooled held-out new-family')
    ax.set_title('Pooled scaffold rule transfer vs dephasing')
    ax.set_xlabel('Dephasing \u03b3')
    ax.set_ylabel('R\u00b2')
    ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def run_phase41_analysis(project_root: Path, output_root: Path | None = None, config: Phase41Config | None = None) -> dict:
    cfg = config or Phase41Config()
    project_root = Path(project_root)
    output_root = project_root if output_root is None else Path(output_root)

    c_path = project_root / 'cgt_benchmarks' / 'results' / cfg.benchmark_c_slug / cfg.benchmark_c_filename
    g_path = project_root / 'cgt_benchmarks' / 'results' / cfg.benchmark_g_slug / cfg.benchmark_g_filename
    c_payload = json.loads(c_path.read_text())
    g_payload = json.loads(g_path.read_text())

    c_levels = {round(float(level['dephasing']), 10): level for level in c_payload['levels']}
    g_levels = {round(float(level['dephasing']), 10): level for level in g_payload['levels']}
    gammas = sorted(set(c_levels).intersection(g_levels))

    levels: list[dict] = []
    c_combined_r2: list[float] = []
    g_combined_r2: list[float] = []
    both_combined_r2: list[float] = []
    both_new_r2: list[float] = []

    for gamma in gammas:
        c_level = c_levels[gamma]
        g_level = g_levels[gamma]

        c_train = _group(c_level['rows'], 'train')
        g_train = _group(g_level['rows'], 'train')
        pooled_rule = _derive_pooled_rule(c_train + g_train)

        c_rows = _augment_rows(c_level['rows'], pooled_rule)
        g_rows = _augment_rows(g_level['rows'], pooled_rule)

        c_train_rows = _group(c_rows, 'train')
        c_base_rows = _group(c_rows, 'heldout_base')
        c_new_rows = _group(c_rows, 'heldout_new')
        c_comb_rows = c_base_rows + c_new_rows

        g_train_rows = _group(g_rows, 'train')
        g_base_rows = _group(g_rows, 'heldout_base')
        g_new_rows = _group(g_rows, 'heldout_new')
        g_comb_rows = g_base_rows + g_new_rows

        both_comb_rows = c_comb_rows + g_comb_rows
        both_new_rows = c_new_rows + g_new_rows

        c_train_fit = _prediction_summary(c_train_rows, 'pooled_positive_noisy_scaffold_predictor')
        c_base_fit = _prediction_summary(c_base_rows, 'pooled_positive_noisy_scaffold_predictor')
        c_new_fit = _prediction_summary(c_new_rows, 'pooled_positive_noisy_scaffold_predictor')
        c_comb_fit = _prediction_summary(c_comb_rows, 'pooled_positive_noisy_scaffold_predictor')

        g_train_fit = _prediction_summary(g_train_rows, 'pooled_positive_noisy_scaffold_predictor')
        g_base_fit = _prediction_summary(g_base_rows, 'pooled_positive_noisy_scaffold_predictor')
        g_new_fit = _prediction_summary(g_new_rows, 'pooled_positive_noisy_scaffold_predictor')
        g_comb_fit = _prediction_summary(g_comb_rows, 'pooled_positive_noisy_scaffold_predictor')

        both_comb_fit = _prediction_summary(both_comb_rows, 'pooled_positive_noisy_scaffold_predictor')
        both_new_fit = _prediction_summary(both_new_rows, 'pooled_positive_noisy_scaffold_predictor')

        c_combined_r2.append(safe_float(c_comb_fit['r2']))
        g_combined_r2.append(safe_float(g_comb_fit['r2']))
        both_combined_r2.append(safe_float(both_comb_fit['r2']))
        both_new_r2.append(safe_float(both_new_fit['r2']))

        levels.append(
            {
                'dephasing': float(gamma),
                'pooled_positive_noisy_scaffold_rule': pooled_rule,
                'benchmark_c': {
                    'train_fit': c_train_fit,
                    'heldout_base_fit': c_base_fit,
                    'heldout_new_fit': c_new_fit,
                    'heldout_combined_fit': c_comb_fit,
                    'rows': c_rows,
                },
                'benchmark_g': {
                    'train_fit': g_train_fit,
                    'heldout_base_fit': g_base_fit,
                    'heldout_new_fit': g_new_fit,
                    'heldout_combined_fit': g_comb_fit,
                    'rows': g_rows,
                },
                'pooled_scaffold': {
                    'heldout_new_fit': both_new_fit,
                    'heldout_combined_fit': both_comb_fit,
                },
            }
        )

    if not levels:
        raise ValueError('No common dephasing levels between benchmarks C and G')
    switch_gamma = float(cfg.default_switch_gamma)
    switch_level = min(levels, key=lambda level: abs(float(level['dephasing']) - switch_gamma))

    c_switch_rows = [r for r in switch_level['benchmark_c']['rows'] if r.get('family_group') != 'train']
    g_switch_rows = [r for r in switch_level['benchmark_g']['rows'] if r.get('family_group') != 'train']

    scatter_path = output_root / 'cgt_benchmarks' / 'reports' / 'plots' / 'phase41_pooled_positive_scaffold' / 'response_vs_pooled_predictor_switch.png'
    lines_path = output_root / 'cgt_benchmarks' / 'reports' / 'plots' / 'phase41_pooled_positive_scaffold' / 'r2_vs_dephasing.png'
    _plot_switch_scatter(scatter_path, c_switch_rows, g_switch_rows)
    _plot_r2_lines(lines_path, list(gammas), c_combined_r2, g_combined_r2, both_combined_r2, both_new_r2)

    pooled_combined_r2 = switch_level['pooled_scaffold']['heldout_combined_fit']['r2']
    pooled_sign_agreement = switch_level['pooled_scaffold']['heldout_combined_fit']['sign_agreement']
    verdict = 'pooled_positive_noisy_scaffold_partial'
    if (
        pooled_combined_r2 is not None
        and pooled_sign_agreement is not None
        and float(pooled_combined_r2) >= 0.90
        and float(pooled_sign_agreement) > 0.5
    ):
        verdict = 'pooled_positive_noisy_scaffold_supported'

    payload = {
        'phase': 'phase41_pooled_positive_noisy_scaffold_rule',
        'description': cfg.description,
        'source_artifacts': {
            'benchmark_c': str(c_path),
            'benchmark_g': str(g_path),
        },
        'dephasing_values': [float(g) for g in gammas],
        'switch_gamma': switch_gamma,
        'switch_level': switch_level,
        'levels': levels,
        'switch_metrics': {
            'benchmark_c_heldout_combined_r2': switch_level['benchmark_c']['heldout_combined_fit']['r2'],
            'benchmark_g_heldout_combined_r2': switch_level['benchmark_g']['heldout_combined_fit']['r2'],
            'benchmark_c_heldout_new_r2': switch_level['benchmark_c']['heldout_new_fit']['r2'],
            'benchmark_g_heldout_new_r2': switch_level['benchmark_g']['heldout_new_fit']['r2'],
            'pooled_heldout_combined_r2': switch_level['pooled_scaffold']['heldout_combined_fit']['r2'],
            'pooled_heldout_new_r2': switch_level['pooled_scaffold']['heldout_new_fit']['r2'],
            'pooled_heldout_combined_corr': switch_level['pooled_scaffold']['heldout_combined_fit']['corr'],
            'sign_agreement': switch_level['pooled_scaffold']['heldout_combined_fit']['sign_agreement'],
        },
        'verdict': verdict,
        'notes': [
            'Train rows are pooled across benchmarks C and G using the same square/circle families.',
            'Held-out base/new families remain untouched for both benchmarks.',
            'This strengthens scaffold-level generalization but remains within designed scaffold benchmarks.',
        ],
    }

    output_path = output_root / 'cgt_benchmarks' / 'results' / 'benchmark_scaffold_family' / 'benchmark_scaffold_phase41_pooled_positive_noisy.json'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(nan_to_none(payload), indent=2))
    return payload


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase41_analysis(project_root=project_root, output_root=project_root)
    print(json.dumps(nan_to_none(payload['switch_metrics']), indent=2))
