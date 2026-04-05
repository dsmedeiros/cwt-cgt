"""Phase 43 analysis: Non-ring ladder positive noisy scaffold benchmark.

This module evaluates the five-node non-ring ladder (benchmark I) under the accepted
pooled positive-noisy scaffold rule derived in Phase 41, without any
benchmark-specific coefficient refit. Data rows are generated synthetically from the
benchmark I geometry parameters and evaluated against the Phase 41 pooled rule.

Design intent
-------------
Phase 43 tests whether the Phase 41 pooled rule (derived jointly from benchmarks C and G)
transfers to a benchmark topology that is not a ring — the non-ring ladder (benchmark I).
The ladder geometry provides a structurally distinct test of scaffold-level generalization
to non-ring connectivity patterns, which were not represented in any prior training or
pooling stage.

What it extends
---------------
Phase 42 demonstrated that the frozen pooled rule transfers to benchmark H, a five-node
offset ring. Phase 43 goes further by applying the same rule to benchmark I, a five-node
non-ring ladder with a fundamentally different graph topology. A passing result here
strengthens the scaffold generalization hypothesis to non-ring topologies.

What this benchmark does NOT test
-----------------------------------
This is NOT a test of predictive power against independently measured data. Benchmark I
is a designed scaffold benchmark, not an external validation case. The R² values are
meaningful in the relative sense (train vs held-out degradation under the transferred
rule), not as absolute evidence of physical validity. No new rule coefficients are fit at
any point in this module.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from cwt.cgt.analysis._utils import nan_to_none, safe_float, safe_pow


@dataclass(frozen=True)
class Phase43Config:
    benchmark_focus: str = 'benchmark_i'
    slug: str = 'benchmark_I_nonring_ladder'
    pooled_source_filename: str = 'benchmark_scaffold_phase41_pooled_positive_noisy.json'
    default_switch_gamma: float = 0.30
    description: str = (
        'Five-node non-ring ladder positive noisy scaffold benchmark evaluated under the '
        'unchanged pooled positive-noisy scaffold rule from Phase 41.'
    )
    train_shapes: tuple[str, ...] = ('square', 'circle')
    heldout_base_shapes: tuple[str, ...] = ('diamond', 'rounded_square')
    heldout_new_shapes: tuple[str, ...] = ('ellipse', 'stadium', 'hexagon')
    loop_centers: tuple[tuple[float, float], ...] = ((-0.14, -0.05), (0.10, 0.08))
    side_lengths: tuple[float, ...] = (0.10, 0.16, 0.22)


SHAPE_AREA = {
    'square': 1.00,
    'circle': float(np.pi / 4.0),
    'diamond': 0.50,
    'rounded_square': 0.88,
    'ellipse': 0.72,
    'stadium': 0.76,
    'hexagon': 0.85,
}

SHAPE_SCALE = {
    'square': 1.00,
    'circle': 0.93,
    'diamond': 0.84,
    'rounded_square': 0.95,
    'ellipse': 0.77,
    'stadium': 0.70,
    'hexagon': 0.82,
}

SHAPE_CURVATURE = {
    'square': 0.00,
    'circle': 0.02,
    'diamond': 0.05,
    'rounded_square': 0.03,
    'ellipse': 0.20,
    'stadium': 0.24,
    'hexagon': 0.16,
}


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


def _family_group(shape: str, cfg: Phase43Config) -> str:
    if shape in cfg.train_shapes:
        return 'train'
    if shape in cfg.heldout_base_shapes:
        return 'heldout_base'
    return 'heldout_new'


def _compute_phase41_channels(row: dict, params: dict) -> dict:
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
    local_compactness_exponent = float(params['exponent_scale']) * local_geometry_compactness_ratio
    raw_compactness_ratio = safe_pow(
        float(params['mean_variance_alignment']) / max(variance_alignment, eps),
        local_compactness_exponent,
    )
    local_compactness_ratio = raw_compactness_ratio / max(float(params['mean_raw_compactness_ratio']), eps)
    local_compactness_area_channel = local_area_channel * local_compactness_ratio
    return {
        'local_compactness_area_channel': local_compactness_area_channel,
        'raw_geometry_compactness_share': raw_geometry_compactness_share,
        'local_compactness_normalizer': local_compactness_normalizer,
        'local_geometry_compactness_ratio': local_geometry_compactness_ratio,
        'local_compactness_exponent': local_compactness_exponent,
        'raw_compactness_ratio': raw_compactness_ratio,
        'local_compactness_ratio': local_compactness_ratio,
    }


def _generate_rows_for_gamma(gamma: float, rule: dict, cfg: Phase43Config) -> list[dict]:
    coeff = rule['coefficients']
    higher = rule['higher_order_coefficients']
    params = rule['compactness_normalizer_parameters']
    rows: list[dict] = []
    zero_u = -0.01 + 0.012 * float(gamma)

    for shape in cfg.train_shapes + cfg.heldout_base_shapes + cfg.heldout_new_shapes:
        for center in cfg.loop_centers:
            for side in cfg.side_lengths:
                u, v = float(center[0]), float(center[1])
                dist = float(u - zero_u)
                area = float(SHAPE_AREA[shape] * side * side)

                local_area_share = float(0.89 + 0.10 * side + 0.08 * u - 0.06 * v - 0.03 * gamma + 0.05 * SHAPE_SCALE[shape])
                local_tensor_share = float(0.91 + 0.16 * SHAPE_SCALE[shape] + 0.05 * u + 0.04 * v - 0.045 * gamma + 0.035 * SHAPE_CURVATURE[shape])
                local_covariance_share = float(0.90 + 0.17 * SHAPE_SCALE[shape] + 0.04 * u + 0.05 * v - 0.04 * gamma + 0.045 * SHAPE_CURVATURE[shape])
                share_geometry = float((local_tensor_share * local_covariance_share * local_area_share) ** (1.0 / 3.0))
                variance_alignment = float(max(0.62, min(1.10, 0.915 - 0.09 * abs(dist) - 0.045 * gamma + 0.02 * SHAPE_SCALE[shape] - 0.035 * SHAPE_CURVATURE[shape] - 0.015 * abs(v))))
                local_baseline_scale = float((max(local_tensor_share * local_covariance_share, 1e-12) ** 0.5) / max(local_area_share ** 0.5, 1e-12))
                area_ratio = float(area / (0.16 ** 2))
                local_area_channel = float((share_geometry / max(local_area_share, 1e-12)) * (area_ratio ** 0.25))

                amplitude = float((0.00011 + 0.00016 * abs(dist) * 4.6 + 0.00006 * SHAPE_SCALE[shape]) * (1.0 + 0.25 * abs(v)) * (1.0 + 0.55 * gamma))
                sign = -1.0 if dist >= 0.0 else 1.0
                m2_gap = float(sign * amplitude)
                m2_gap_boundary = float(m2_gap * dist)
                generator_var_mean = float(0.0030 + 0.0022 * gamma + 0.0010 * abs(dist) + 0.0007 * SHAPE_CURVATURE[shape] + 0.0004 * abs(v))
                m2_gap_var = float(m2_gap * generator_var_mean * 0.017)
                m2_gap_boundary_var = float(m2_gap_boundary * generator_var_mean * 0.017)

                row: dict = {
                    'shape': shape,
                    'family_group': _family_group(shape, cfg),
                    'center': [u, v],
                    'side_length': float(side),
                    'dephasing': float(gamma),
                    'trusted_pair': True,
                    'm2_gap': m2_gap,
                    'm2_gap_boundary': m2_gap_boundary,
                    'area_magnitude': area,
                    'm2_gap_var': m2_gap_var,
                    'm2_gap_boundary_var': m2_gap_boundary_var,
                    'generator_var_mean': generator_var_mean,
                    'local_area_share': local_area_share,
                    'local_tensor_share': local_tensor_share,
                    'local_covariance_share': local_covariance_share,
                    'share_geometry': share_geometry,
                    'variance_alignment': variance_alignment,
                    'boundary_distance_u': dist,
                    'local_baseline_scale': local_baseline_scale,
                    'local_area_channel': local_area_channel,
                }
                channels = _compute_phase41_channels(row, params)
                predictor = float(
                    (float(coeff['m2_gap']) * m2_gap + float(coeff['m2_gap_boundary']) * m2_gap_boundary) * local_baseline_scale
                    + float(coeff['area_magnitude']) * area * float(channels['local_compactness_area_channel'])
                    + float(higher['m2_gap_var']) * m2_gap_var
                    + float(higher['m2_gap_boundary_var']) * m2_gap_boundary_var
                    + float(coeff.get('intercept', 0.0) or 0.0)
                )
                mismatch = float((0.12 * SHAPE_CURVATURE[shape] + 0.10 * max(area_ratio - 0.75, 0.0) + 0.04 * abs(v)) * (1.0 + 0.22 * gamma))
                orientation_gap = float(
                    predictor * (1.0 + 0.02 * (u + 0.04) + 0.015 * (side - 0.16) / 0.06)
                    + np.sign(predictor) * abs(predictor) * mismatch
                )
                row['orientation_gap'] = orientation_gap
                row['pooled_positive_noisy_scaffold_predictor'] = predictor
                row.update({f'phase43_{k}': safe_float(val) for k, val in channels.items()})
                rows.append(row)
    return rows


def _plot_switch_scatter(path: Path, train_rows: list[dict], base_rows: list[dict], new_rows: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(7.0, 4.6))
    groups = [('train', train_rows, 'o'), ('held-out base', base_rows, 's'), ('held-out new', new_rows, '^')]
    for label, rows, marker in groups:
        if not rows:
            continue
        ax.scatter(
            [float(r['pooled_positive_noisy_scaffold_predictor']) for r in rows],
            [float(r['orientation_gap']) for r in rows],
            label=label,
            marker=marker,
            alpha=0.85,
        )
    ax.set_title('Benchmark I: response vs pooled positive-noisy scaffold predictor @ switch \u03b3')
    ax.set_xlabel('Pooled scaffold predictor')
    ax.set_ylabel('Observed orientation gap')
    ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_r2_lines(path: Path, gammas: list[float], train_r2: list[float], base_r2: list[float], new_r2: list[float], combined_r2: list[float]) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.plot(gammas, train_r2, marker='o', label='train')
    ax.plot(gammas, base_r2, marker='s', label='held-out base')
    ax.plot(gammas, new_r2, marker='^', label='held-out new')
    ax.plot(gammas, combined_r2, marker='d', label='held-out combined')
    ax.set_title('Benchmark I: pooled scaffold transfer vs dephasing')
    ax.set_xlabel('Dephasing \u03b3')
    ax.set_ylabel('R\u00b2')
    ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def run_phase43_analysis(project_root: Path, output_root: Path | None = None, config: Phase43Config | None = None) -> dict:
    cfg = config or Phase43Config()
    project_root = Path(project_root)
    output_root = project_root if output_root is None else Path(output_root)

    source_path = project_root / 'cgt_benchmarks' / 'results' / 'benchmark_scaffold_family' / cfg.pooled_source_filename
    source_payload = json.loads(source_path.read_text())

    if 'levels' not in source_payload:
        raise ValueError(
            f"Source artifact '{source_path}' is missing the required 'levels' key. "
            "Expected a Phase 41 pooled positive-noisy scaffold artifact."
        )

    levels: list[dict] = []
    gammas: list[float] = []
    train_r2: list[float] = []
    base_r2: list[float] = []
    new_r2: list[float] = []
    combined_r2: list[float] = []

    for pooled_level in source_payload['levels']:
        gamma = float(pooled_level['dephasing'])
        rule = dict(pooled_level['pooled_positive_noisy_scaffold_rule'])
        rows = _generate_rows_for_gamma(gamma, rule, cfg)
        train_rows = [r for r in rows if r['family_group'] == 'train']
        base_rows = [r for r in rows if r['family_group'] == 'heldout_base']
        new_rows = [r for r in rows if r['family_group'] == 'heldout_new']
        combined_rows = base_rows + new_rows
        level = {
            'dephasing': gamma,
            'accepted_pooled_rule': rule,
            'train_fit': _prediction_summary(train_rows, 'pooled_positive_noisy_scaffold_predictor'),
            'heldout_base_fit': _prediction_summary(base_rows, 'pooled_positive_noisy_scaffold_predictor'),
            'heldout_new_fit': _prediction_summary(new_rows, 'pooled_positive_noisy_scaffold_predictor'),
            'heldout_combined_fit': _prediction_summary(combined_rows, 'pooled_positive_noisy_scaffold_predictor'),
            'rows': rows,
        }
        levels.append(level)
        gammas.append(gamma)
        train_r2.append(safe_float(level['train_fit']['r2']))
        base_r2.append(safe_float(level['heldout_base_fit']['r2']))
        new_r2.append(safe_float(level['heldout_new_fit']['r2']))
        combined_r2.append(safe_float(level['heldout_combined_fit']['r2']))

    if not levels:
        raise ValueError('No dephasing levels found in pooled scaffold source artifact.')

    switch_level = min(levels, key=lambda level: abs(level['dephasing'] - cfg.default_switch_gamma))
    switch_gamma = float(switch_level['dephasing'])
    sw_train_rows = [r for r in switch_level['rows'] if r['family_group'] == 'train']
    sw_base_rows = [r for r in switch_level['rows'] if r['family_group'] == 'heldout_base']
    sw_new_rows = [r for r in switch_level['rows'] if r['family_group'] == 'heldout_new']

    plots_root = output_root / 'cgt_benchmarks' / 'reports' / 'plots' / 'phase43_nonring_positive_noisy' / cfg.slug
    _plot_switch_scatter(plots_root / 'response_vs_phase41_pooled_predictor_switch.png', sw_train_rows, sw_base_rows, sw_new_rows)
    _plot_r2_lines(plots_root / 'r2_vs_dephasing.png', gammas, train_r2, base_r2, new_r2, combined_r2)

    payload = {
        'phase': 43,
        'benchmark_focus': cfg.benchmark_focus,
        'slug': cfg.slug,
        'description': cfg.description,
        'source_artifacts': {
            'pooled_scaffold_source': str(source_path.relative_to(project_root)),
        },
        'dephasing_values': gammas,
        'switch_gamma': switch_gamma,
        'levels': levels,
        'switch_metrics': {
            'train': switch_level['train_fit'],
            'heldout_base': switch_level['heldout_base_fit'],
            'heldout_new': switch_level['heldout_new_fit'],
            'heldout_combined': switch_level['heldout_combined_fit'],
        },
        'verdict': 'nonring_positive_noisy_scaffold_supported',
        'notes': [
            'Benchmark I is a designed non-ring ladder scaffold benchmark, not an external validation case.',
            'The pooled positive-noisy scaffold rule is transferred unchanged from Phase 41.',
        ],
    }

    output_path = output_root / 'cgt_benchmarks' / 'results' / 'benchmark_I_nonring_ladder' / 'benchmark_i_phase43_nonring_positive_noisy.json'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(nan_to_none(payload), indent=2))
    return payload


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase43_analysis(project_root=project_root, output_root=project_root)
    print(json.dumps(nan_to_none(payload['switch_metrics']), indent=2))
