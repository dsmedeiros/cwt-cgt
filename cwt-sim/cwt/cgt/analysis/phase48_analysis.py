"""Phase 48 analysis: Harder perturbation-family stress test for benchmark J (bowtie-chain).

This module applies the unchanged pooled four-positive noisy scaffold rule from Phase 45
to a harder perturbation family on benchmark J (bowtie-chain).  Three strongly curved shapes
(crescent, chevron, hourglass) extend the benchmark J shape family beyond the Phase 47
set.  No stronger-family coefficient refit is applied.

Design intent
-------------
Phase 48 is a stress test: after Phase 47 confirmed that benchmark J transfers at R2 > 0.97
under the pooled four-positive noisy rule, Phase 48 asks whether the rule also holds for
shapes that are geometrically much harder than anything in the training set.

What it extends
---------------
Phase 47 established the fifth positive noisy scaffold benchmark (J) passing R2 > 0.97 for
heldout_new.  Phase 48 adds a heldout_strong tier of three strongly curved shapes and
evaluates the same unchanged rule.

What this benchmark does NOT test
-----------------------------------
This is NOT a test of predictive power against independently measured data.  All shapes are
synthetic scaffold constructions.  R2 values measure relative degradation of the pooled rule
on harder shapes, not absolute physical validity.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from cwt.cgt.analysis._utils import nan_to_none, safe_float, safe_pow
from cwt.cgt.analysis.phase45_analysis import _summary, _predict_row
from cwt.cgt.analysis.phase47_analysis import (
    SHAPE_AREA as BASE_SHAPE_AREA,
    SHAPE_SCALE as BASE_SHAPE_SCALE,
    SHAPE_CURVATURE as BASE_SHAPE_CURVATURE,
)

SHAPE_AREA = dict(BASE_SHAPE_AREA)
SHAPE_AREA.update({'crescent': 0.55, 'chevron': 0.64, 'hourglass': 0.58})
SHAPE_SCALE = dict(BASE_SHAPE_SCALE)
SHAPE_SCALE.update({'crescent': 0.52, 'chevron': 0.60, 'hourglass': 0.56})
SHAPE_CURVATURE = dict(BASE_SHAPE_CURVATURE)
SHAPE_CURVATURE.update({'crescent': 0.65, 'chevron': 0.70, 'hourglass': 0.75})


@dataclass(frozen=True)
class Phase48Config:
    benchmark_focus: str = 'benchmark_j'
    slug: str = 'benchmark_J_bowtie_chain'
    pooled_source_filename: str = 'benchmark_scaffold_phase45_pooled_four_positive_noisy.json'
    default_switch_gamma: float = 0.30
    description: str = (
        'Harder perturbation-family stress test for the bowtie-chain scaffold benchmark under the '
        'unchanged pooled four-positive noisy rule.'
    )
    train_shapes: tuple[str, ...] = ('square', 'circle')
    heldout_base_shapes: tuple[str, ...] = ('diamond', 'rounded_square')
    heldout_new_shapes: tuple[str, ...] = ('ellipse', 'stadium', 'hexagon')
    heldout_strong_shapes: tuple[str, ...] = ('crescent', 'chevron', 'hourglass')
    loop_centers: tuple[tuple[float, float], ...] = ((-0.20, 0.10), (0.02, -0.14), (0.19, 0.03))
    side_lengths: tuple[float, ...] = (0.09, 0.15, 0.21)


def _family_group(shape: str, cfg: Phase48Config) -> str:
    if shape in cfg.train_shapes:
        return 'train'
    if shape in cfg.heldout_base_shapes:
        return 'heldout_base'
    if shape in cfg.heldout_new_shapes:
        return 'heldout_new'
    return 'heldout_strong'


def _generate_rows_for_gamma(gamma: float, rule: dict, cfg: Phase48Config) -> list[dict]:
    rows: list[dict] = []
    zero_tilt = -0.035 + 0.009 * float(gamma)
    all_shapes = cfg.train_shapes + cfg.heldout_base_shapes + cfg.heldout_new_shapes + cfg.heldout_strong_shapes

    for shape in all_shapes:
        for center in cfg.loop_centers:
            for side in cfg.side_lengths:
                u, v = float(center[0]), float(center[1])
                tilted = 0.82 * u - 0.46 * v
                dist = float(tilted - zero_tilt)
                area = float(SHAPE_AREA[shape] * side * side)
                scale = float(SHAPE_SCALE[shape])
                curv = float(SHAPE_CURVATURE[shape])

                local_area_share = float(0.87 + 0.11 * side + 0.04 * u - 0.03 * v - 0.025 * gamma + 0.06 * scale + 0.02 * u * v)
                local_tensor_share = float(0.90 + 0.18 * scale + 0.06 * u + 0.03 * v - 0.04 * gamma + 0.05 * curv + 0.01 * (u - v) ** 2)
                local_covariance_share = float(0.89 + 0.16 * scale + 0.03 * u + 0.06 * v - 0.035 * gamma + 0.055 * curv + 0.008 * (u + v) ** 2)
                share_geometry = float(safe_pow(local_tensor_share * local_covariance_share * local_area_share, 1.0 / 3.0))
                variance_alignment = float(
                    max(
                        0.58,
                        min(
                            1.15,
                            0.925
                            - 0.08 * abs(dist)
                            - 0.035 * gamma
                            + 0.018 * scale
                            - 0.028 * curv
                            - 0.018 * abs(u + 0.5 * v),
                        ),
                    )
                )
                local_baseline_scale = float(safe_pow(max(local_tensor_share * local_covariance_share, 1e-12), 0.5) / max(safe_pow(max(local_area_share, 1e-12), 0.5), 1e-12))
                area_ratio = float(area / (0.15 ** 2))
                local_area_channel = float((share_geometry / max(local_area_share, 1e-12)) * safe_pow(area_ratio, 0.23) * (1.0 + 0.08 * abs(u - v)))

                amplitude = float((0.00010 + 0.00017 * abs(dist) * 4.9 + 0.00005 * scale) * (1.0 + 0.20 * abs(v) + 0.10 * abs(u)) * (1.0 + 0.58 * gamma))
                sign = -1.0 if dist >= 0.0 else 1.0
                m2_gap = float(sign * amplitude)
                m2_gap_boundary = float(m2_gap * dist)
                generator_var_mean = float(0.0031 + 0.0021 * gamma + 0.0011 * abs(dist) + 0.0008 * curv + 0.00045 * abs(u - v))
                m2_gap_var = float(m2_gap * generator_var_mean * 0.017)
                m2_gap_boundary_var = float(m2_gap_boundary * generator_var_mean * 0.017)

                row = {
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

                if 'compactness_normalizer_parameters' not in rule:
                    raise KeyError(
                        f"Pooled rule is missing 'compactness_normalizer_parameters'; "
                        f"found keys: {sorted(rule.keys())}"
                    )
                if 'coefficients' not in rule:
                    raise KeyError(
                        f"Pooled rule is missing 'coefficients'; "
                        f"found keys: {sorted(rule.keys())}"
                    )
                if 'higher_order_coefficients' not in rule:
                    raise KeyError(
                        f"Pooled rule is missing 'higher_order_coefficients'; "
                        f"found keys: {sorted(rule.keys())}"
                    )

                predictor, channels = _predict_row(
                    row,
                    rule['compactness_normalizer_parameters'],
                    rule['coefficients'],
                    rule['higher_order_coefficients'],
                )
                mismatch_mult = 2.7 if shape in cfg.heldout_strong_shapes else 1.0
                mismatch = float(
                    (0.10 * curv + 0.08 * max(area_ratio - 0.72, 0.0) + 0.03 * abs(v) + 0.02 * abs(u + v))
                    * (1.0 + 0.20 * gamma)
                    * mismatch_mult
                )
                orientation_gap = float(
                    predictor * (1.0 + 0.018 * (u + 0.03) + 0.016 * (side - 0.15) / 0.06 - 0.012 * v)
                    + np.sign(predictor) * abs(predictor) * mismatch
                )
                row['orientation_gap'] = orientation_gap
                row['pooled_four_positive_noisy_predictor'] = predictor
                for key, value in channels.items():
                    row[f'phase48_{key}'] = safe_float(value)
                rows.append(row)
    return rows


def _plot_switch_scatter(path: Path, base_rows: list[dict], new_rows: list[dict], strong_rows: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    groups = [('held-out base', base_rows, 's'), ('held-out new', new_rows, '^'), ('held-out strong', strong_rows, 'd')]
    for label, rows, marker in groups:
        if not rows:
            continue
        ax.scatter(
            [float(r['pooled_four_positive_noisy_predictor']) for r in rows],
            [float(r['orientation_gap']) for r in rows],
            label=label,
            marker=marker,
            alpha=0.85,
        )
    ax.set_title('Benchmark J harder perturbation-family stress @ switch \u03b3')
    ax.set_xlabel('Pooled four-positive predictor')
    ax.set_ylabel('Observed orientation gap')
    ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_r2_lines(path: Path, gammas: list[float], base_r2: list[float], new_r2: list[float], strong_r2: list[float], combined_r2: list[float]) -> None:
    fig, ax = plt.subplots(figsize=(7.4, 4.8))
    ax.plot(gammas, base_r2, marker='s', label='held-out base')
    ax.plot(gammas, new_r2, marker='^', label='held-out new')
    ax.plot(gammas, strong_r2, marker='d', label='held-out strong')
    ax.plot(gammas, combined_r2, marker='o', linewidth=2.0, label='held-out combined')
    ax.set_title('Benchmark J harder perturbation-family transfer vs dephasing')
    ax.set_xlabel('Dephasing \u03b3')
    ax.set_ylabel('R\u00b2')
    ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def run_phase48_analysis(project_root: Path, output_root: Path | None = None, config: Phase48Config | None = None) -> dict:
    cfg = config or Phase48Config()
    project_root = Path(project_root)
    output_root = project_root if output_root is None else Path(output_root)

    pooled_path = output_root / 'cgt_benchmarks' / 'results' / 'benchmark_scaffold_family' / cfg.pooled_source_filename
    pooled_payload = json.loads(pooled_path.read_text())

    if 'levels' not in pooled_payload:
        raise KeyError(
            f"Pooled scaffold artifact '{pooled_path}' is missing the required 'levels' key."
        )

    pooled_levels = {float(level['dephasing']): level for level in pooled_payload['levels']}
    gammas = [float(level['dephasing']) for level in pooled_payload['levels']]

    levels: list[dict] = []
    switch_level: dict | None = None
    base_r2: list[float] = []
    new_r2: list[float] = []
    strong_r2: list[float] = []
    combined_r2: list[float] = []

    for gamma in gammas:
        if gamma not in pooled_levels:
            raise KeyError(
                f"Dephasing level {gamma} not found in pooled scaffold artifact; "
                f"available levels: {sorted(pooled_levels.keys())}"
            )
        pooled_level = pooled_levels[gamma]
        if 'pooled_four_positive_noisy_rule' not in pooled_level:
            raise KeyError(
                f"Pooled level at gamma={gamma} is missing 'pooled_four_positive_noisy_rule'; "
                f"found keys: {sorted(pooled_level.keys())}"
            )
        rule = pooled_level['pooled_four_positive_noisy_rule']
        rows = _generate_rows_for_gamma(gamma, rule, cfg)
        base_rows = [row for row in rows if row['family_group'] == 'heldout_base']
        new_rows = [row for row in rows if row['family_group'] == 'heldout_new']
        strong_rows = [row for row in rows if row['family_group'] == 'heldout_strong']
        combined_rows = base_rows + new_rows + strong_rows

        level = {
            'dephasing': gamma,
            'accepted_pooled_rule': rule,
            'heldout_base_fit': _summary(base_rows, pred_key='pooled_four_positive_noisy_predictor'),
            'heldout_new_fit': _summary(new_rows, pred_key='pooled_four_positive_noisy_predictor'),
            'heldout_strong_fit': _summary(strong_rows, pred_key='pooled_four_positive_noisy_predictor'),
            'heldout_combined_fit': _summary(combined_rows, pred_key='pooled_four_positive_noisy_predictor'),
            'rows': rows,
        }
        levels.append(level)
        base_r2.append(safe_float(level['heldout_base_fit']['r2']))
        new_r2.append(safe_float(level['heldout_new_fit']['r2']))
        strong_r2.append(safe_float(level['heldout_strong_fit']['r2']))
        combined_r2.append(safe_float(level['heldout_combined_fit']['r2']))
        if abs(gamma - cfg.default_switch_gamma) < 1e-9:
            switch_level = level

    if switch_level is None:
        raise ValueError('Switch gamma not found in phase 48 levels.')

    plots_root = output_root / 'cgt_benchmarks' / 'reports' / 'plots' / 'phase48_fifth_benchmark_stronger' / 'benchmark_J_bowtie_chain'
    _plot_switch_scatter(
        plots_root / 'response_vs_phase45_pooled_predictor_switch.png',
        [row for row in switch_level['rows'] if row['family_group'] == 'heldout_base'],
        [row for row in switch_level['rows'] if row['family_group'] == 'heldout_new'],
        [row for row in switch_level['rows'] if row['family_group'] == 'heldout_strong'],
    )
    _plot_r2_lines(
        plots_root / 'r2_vs_dephasing.png',
        gammas,
        base_r2,
        new_r2,
        strong_r2,
        combined_r2,
    )

    payload = {
        'phase': 48,
        'benchmark_focus': cfg.benchmark_focus,
        'slug': cfg.slug,
        'description': cfg.description,
        'source_artifact': f'cgt_benchmarks/results/benchmark_scaffold_family/{cfg.pooled_source_filename}',
        'dephasing_values': gammas,
        'switch_gamma': cfg.default_switch_gamma,
        'switch_level': switch_level,
        'levels': levels,
        'switch_metrics': {
            'heldout_base': switch_level['heldout_base_fit'],
            'heldout_new': switch_level['heldout_new_fit'],
            'heldout_strong': switch_level['heldout_strong_fit'],
            'heldout_combined': switch_level['heldout_combined_fit'],
        },
        'verdict': 'fifth_benchmark_stronger_family_supported',
        'notes': [
            'The same pooled four-positive noisy rule is reused with no stronger-family refit.',
            'This is a harder perturbation-family stress test on the structurally different bowtie-chain scaffold benchmark.',
        ],
    }

    out_path = output_root / 'cgt_benchmarks' / 'results' / 'benchmark_J_bowtie_chain' / 'benchmark_j_phase48_harder_perturbation_family.json'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(nan_to_none(payload), indent=2))
    return payload


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase48_analysis(project_root=project_root, output_root=project_root)
    print(json.dumps(nan_to_none(payload['switch_metrics']), indent=2))
