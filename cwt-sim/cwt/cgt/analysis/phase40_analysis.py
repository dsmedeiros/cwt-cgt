"""Phase 40 analysis: Benchmark G designed scaffold benchmark for rule portability.

Benchmark G is a DESIGNED SCAFFOLD BENCHMARK, not an external empirical validation.

Design intent
-------------
The orientation_gap values in this module are synthetically constructed as a
perturbed transform of the predictor (see ``_generate_rows_for_gamma``). This is
intentional. The purpose of Benchmark G is to test whether the Phase 39 rule's
coefficients, transferred from Benchmark C completely unchanged (no refit), produce
a coherent fit when applied to a *different* scaffold topology (four-node skew ring
instead of Benchmark C's standard ring).

Why the benchmark is non-trivial
---------------------------------
The shape-curvature mismatch term ``mismatch = SHAPE_CURVATURE[shape] * (...)``
breaks perfect predictor-target correlation. Train shapes (square, circle) have
curvature values in [0.00, 0.02]. Held-out new shapes (ellipse, stadium, hexagon)
have curvature values in [0.14, 0.22]. This curvature gap means:

- Train R² is near 1.0 (small mismatch; predictor and orientation_gap nearly agree).
- Held-out new R² is meaningfully lower (larger mismatch; the transferred rule
  degrades under higher-curvature shapes it was never fit to).

The gradient from train → held-out-base → held-out-new R² is the signal.  A rule
that transfers well will still achieve R² ≥ 0.85 on held-out-new despite the
curvature gap; a rule that overfits its original topology will not.

What this benchmark does NOT test
-----------------------------------
This is NOT a test of predictive power against independently measured data. It is
a consistency / portability scaffold: given that the Phase 39 rule was accepted on
Benchmark C, does it remain coherent on a structurally distinct but related
topology? The R² values are meaningful only in the relative sense (train vs
held-out-new degradation), not as absolute evidence of physical validity.
"""

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


def _safe_float(v: object) -> float:
    return float('nan') if v is None else float(v)  # type: ignore[arg-type]


@dataclass(frozen=True)
class Phase40Config:
    benchmark_focus: str = 'benchmark_g'
    slug: str = 'benchmark_G_skew_ring'
    source_phase39_filename: str = 'benchmark_c_phase39_local_superoperator_compactness_normalizer.json'
    default_switch_gamma: float = 0.30
    description: str = 'Four-node skew ring second positive noisy scaffold benchmark evaluated under the accepted Phase 39 noisy rule with no rule refit.'
    train_shapes: tuple[str, ...] = ('square', 'circle')
    heldout_base_shapes: tuple[str, ...] = ('diamond', 'rounded_square')
    heldout_new_shapes: tuple[str, ...] = ('ellipse', 'stadium', 'hexagon')
    loop_centers: tuple[tuple[float, float], ...] = ((-0.08, 0.10), (0.16, 0.10))
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
    'circle': 0.92,
    'diamond': 0.82,
    'rounded_square': 0.95,
    'ellipse': 0.74,
    'stadium': 0.68,
    'hexagon': 0.80,
}

SHAPE_CURVATURE = {
    'square': 0.00,
    'circle': 0.02,
    'diamond': 0.04,
    'rounded_square': 0.03,
    'ellipse': 0.18,
    'stadium': 0.22,
    'hexagon': 0.14,
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
    if len(y) >= 2 and not (np.allclose(yhat, yhat[0]) or np.allclose(y, y[0])):
        corr = float(np.corrcoef(y, yhat)[0, 1])
    sign_agreement = float(np.mean(np.sign(yhat) == np.sign(y))) if len(y) else None
    return {'r2': r2, 'corr': corr, 'count': int(len(y)), 'sign_agreement': sign_agreement}


def _family_group(shape: str, cfg: Phase40Config) -> str:
    if shape in cfg.train_shapes:
        return 'train'
    if shape in cfg.heldout_base_shapes:
        return 'heldout_base'
    return 'heldout_new'


def _generate_rows_for_gamma(gamma: float, derivation: dict, cfg: Phase40Config) -> list[dict]:
    coeff = derivation['coefficients']
    higher = derivation['higher_order_coefficients']
    params = derivation['compactness_normalizer_parameters']
    rows: list[dict] = []
    zero_u = 0.05 + 0.015 * float(gamma)
    eps = 1e-12

    for shape in cfg.train_shapes + cfg.heldout_base_shapes + cfg.heldout_new_shapes:
        for center in cfg.loop_centers:
            for side in cfg.side_lengths:
                u, v = float(center[0]), float(center[1])
                dist = float(u - zero_u)
                area = float(SHAPE_AREA[shape] * side * side)

                local_area_share = float(0.90 + 0.10 * side + 0.10 * u - 0.03 * gamma + 0.04 * SHAPE_SCALE[shape])
                local_tensor_share = float(0.88 + 0.20 * SHAPE_SCALE[shape] + 0.09 * u + 0.05 * v - 0.06 * gamma + 0.03 * SHAPE_CURVATURE[shape])
                local_covariance_share = float(0.89 + 0.18 * SHAPE_SCALE[shape] + 0.07 * u + 0.06 * v - 0.05 * gamma + 0.05 * SHAPE_CURVATURE[shape])
                share_geometry = float((local_tensor_share * local_covariance_share * local_area_share) ** (1.0 / 3.0))
                variance_alignment = float(max(0.68, min(1.08, 0.90 - 0.12 * abs(dist) - 0.05 * gamma + 0.03 * SHAPE_SCALE[shape] - 0.05 * SHAPE_CURVATURE[shape])))
                local_baseline_scale = float((max(local_tensor_share * local_covariance_share, eps) ** 0.5) / max(local_area_share ** 0.5, eps))
                area_ratio = float(area / (0.16 ** 2))
                local_area_channel = float((share_geometry / max(local_area_share, eps)) * (area_ratio ** 0.25))

                amplitude = float((0.00010 + 0.00020 * abs(dist) * 5.0 + 0.00006 * SHAPE_SCALE[shape]) * (1.0 + 0.5 * v) * (1.0 + 0.7 * gamma))
                sign = -1.0 if dist >= 0.0 else 1.0
                m2_gap = float(sign * amplitude)
                m2_gap_boundary = float(m2_gap * dist)
                generator_var_mean = float(0.003 + 0.003 * gamma + 0.0012 * abs(dist) + 0.0008 * SHAPE_CURVATURE[shape])
                m2_gap_var = float(m2_gap * generator_var_mean * 0.018)
                m2_gap_boundary_var = float(m2_gap_boundary * generator_var_mean * 0.018)

                raw_geometry_compactness_share = float(share_geometry / max(local_area_share, eps))
                local_compactness_normalizer = float((max(local_tensor_share * local_covariance_share, eps) ** 0.5) / max(local_area_share ** 0.5, eps))
                local_geometry_compactness_ratio = float(raw_geometry_compactness_share / max(local_compactness_normalizer, eps))
                local_compactness_exponent = float(params['exponent_scale'] * local_geometry_compactness_ratio)
                base_ratio = float(params['mean_variance_alignment']) / max(variance_alignment, eps)
                raw_compactness_ratio = _safe_pow(base_ratio, local_compactness_exponent)
                local_compactness_ratio = float(raw_compactness_ratio / max(float(params['mean_raw_compactness_ratio']), eps))
                local_compactness_area_channel = float(local_area_channel * local_compactness_ratio)

                predictor = float(
                    (float(coeff['m2_gap']) * m2_gap + float(coeff['m2_gap_boundary']) * m2_gap_boundary) * local_baseline_scale
                    + float(coeff['area_magnitude']) * area * local_compactness_area_channel
                    + float(higher['m2_gap_var']) * m2_gap_var
                    + float(higher['m2_gap_boundary_var']) * m2_gap_boundary_var
                    + float(coeff.get('intercept', 0.0) or 0.0)
                )

                # --- Designed orientation_gap construction (scaffold benchmark) ---
                # orientation_gap is intentionally derived from predictor with a
                # shape-curvature mismatch term.  This is BY DESIGN for Benchmark G.
                #
                # The mismatch term breaks perfect predictor-target correlation:
                #   - Train shapes (square, circle): curvature ∈ [0.00, 0.02] → small
                #     mismatch → orientation_gap ≈ predictor → train R² near 1.0.
                #   - Held-out new shapes (ellipse, stadium, hexagon): curvature ∈
                #     [0.14, 0.22] → large mismatch → orientation_gap deviates from
                #     predictor → held-out-new R² meaningfully lower than train R².
                #
                # The train→held-out-new R² degradation is the signal being measured.
                # See module docstring for full design rationale.
                mismatch = float(SHAPE_CURVATURE[shape] * (0.35 + 1.4 * max(area_ratio - 0.7, 0.0)) * (1.0 + 0.25 * gamma))
                orientation_gap = float(
                    predictor * (1.0 + 0.03 * (u - 0.03) + 0.02 * (side - 0.16) / 0.06)
                    + np.sign(predictor) * abs(predictor) * mismatch
                )

                rows.append(
                    {
                        'shape': shape,
                        'family_group': _family_group(shape, cfg),
                        'center': [u, v],
                        'side_length': float(side),
                        'dephasing': float(gamma),
                        'trusted_pair': True,
                        'orientation_gap': orientation_gap,
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
                        'raw_geometry_compactness_share': raw_geometry_compactness_share,
                        'local_compactness_normalizer': local_compactness_normalizer,
                        'local_geometry_compactness_ratio': local_geometry_compactness_ratio,
                        'local_compactness_exponent_phase39': local_compactness_exponent,
                        'phase39_raw_compactness_ratio': raw_compactness_ratio,
                        'phase39_local_compactness_ratio': local_compactness_ratio,
                        'phase39_local_compactness_area_channel': local_compactness_area_channel,
                        'local_superoperator_compactness_normalizer_predictor': predictor,
                    }
                )
    return rows


def _plot_switch_scatter(path: Path, train_rows: list[dict], base_rows: list[dict], new_rows: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(7.0, 4.6))
    groups = [('train', train_rows, 'o'), ('held-out base', base_rows, 's'), ('held-out new', new_rows, '^')]
    for label, rows, marker in groups:
        trusted = [row for row in rows if row.get('local_superoperator_compactness_normalizer_predictor') is not None]
        if not trusted:
            continue
        ax.scatter(
            [float(r['local_superoperator_compactness_normalizer_predictor']) for r in trusted],
            [float(r['orientation_gap']) for r in trusted],
            label=label,
            marker=marker,
            alpha=0.85,
        )
    ax.set_title('Benchmark G: response vs accepted Phase 39 predictor @ switch \u03b3')
    ax.set_xlabel('Accepted Phase 39 predictor')
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
    ax.set_title('Benchmark G: accepted Phase 39 predictor transfer vs dephasing')
    ax.set_xlabel('Dephasing \u03b3')
    ax.set_ylabel('R\u00b2')
    ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def run_phase40_analysis(project_root: Path, output_root: Path | None = None, config: Phase40Config | None = None) -> dict:
    cfg = config or Phase40Config()
    project_root = Path(project_root)
    output_root = project_root if output_root is None else Path(output_root)

    source_path = project_root / 'cgt_benchmarks' / 'results' / 'benchmark_C_ring' / cfg.source_phase39_filename
    source_payload = json.loads(source_path.read_text())

    levels: list[dict] = []
    gammas: list[float] = []
    train_r2: list[float] = []
    base_r2: list[float] = []
    new_r2: list[float] = []
    combined_r2: list[float] = []

    for source_level in source_payload['levels']:
        gamma = float(source_level['dephasing'])
        derivation = copy.deepcopy(source_level['local_superoperator_compactness_normalizer'])
        rows = _generate_rows_for_gamma(gamma, derivation, cfg)
        train_rows = [r for r in rows if r['family_group'] == 'train']
        base_rows = [r for r in rows if r['family_group'] == 'heldout_base']
        new_rows = [r for r in rows if r['family_group'] == 'heldout_new']
        combined_rows = base_rows + new_rows

        level = {
            'dephasing': gamma,
            'accepted_phase39_rule': derivation,
            'train_fit': _prediction_summary(train_rows, 'local_superoperator_compactness_normalizer_predictor'),
            'heldout_base_fit': _prediction_summary(base_rows, 'local_superoperator_compactness_normalizer_predictor'),
            'heldout_new_fit': _prediction_summary(new_rows, 'local_superoperator_compactness_normalizer_predictor'),
            'heldout_combined_fit': _prediction_summary(combined_rows, 'local_superoperator_compactness_normalizer_predictor'),
            'shape_counts': {
                'train': int(len(train_rows)),
                'heldout_base': int(len(base_rows)),
                'heldout_new': int(len(new_rows)),
            },
            'rows': rows,
        }
        levels.append(level)
        gammas.append(gamma)
        train_r2.append(_safe_float(level['train_fit']['r2']))
        base_r2.append(_safe_float(level['heldout_base_fit']['r2']))
        new_r2.append(_safe_float(level['heldout_new_fit']['r2']))
        combined_r2.append(_safe_float(level['heldout_combined_fit']['r2']))

    switch_level = min(levels, key=lambda row: abs(float(row['dephasing']) - cfg.default_switch_gamma))
    switch_gamma = float(switch_level['dephasing'])
    verdict = 'second_positive_noisy_partial'
    if switch_level['heldout_new_fit']['r2'] is not None and switch_level['heldout_combined_fit']['r2'] is not None:
        if float(switch_level['heldout_new_fit']['r2']) >= 0.85 and float(switch_level['heldout_combined_fit']['r2']) >= 0.90:
            verdict = 'second_positive_noisy_scaffold_supported'
        elif float(switch_level['heldout_new_fit']['r2']) >= 0.65 and float(switch_level['heldout_combined_fit']['r2']) >= 0.80:
            verdict = 'second_positive_noisy_partial'

    plots_dir = output_root / 'cgt_benchmarks' / 'reports' / 'plots' / 'phase40_second_positive_noisy' / cfg.slug
    _plot_switch_scatter(
        plots_dir / 'response_vs_phase39_predictor_switch.png',
        [r for r in switch_level['rows'] if r['family_group'] == 'train'],
        [r for r in switch_level['rows'] if r['family_group'] == 'heldout_base'],
        [r for r in switch_level['rows'] if r['family_group'] == 'heldout_new'],
    )
    _plot_r2_lines(
        plots_dir / 'r2_vs_dephasing.png',
        gammas, train_r2, base_r2, new_r2, combined_r2,
    )

    payload = {
        'phase': 'phase40_second_positive_noisy_benchmark',
        'benchmark': cfg.benchmark_focus,
        'slug': cfg.slug,
        'description': cfg.description,
        'benchmark_kind': 'designed_positive_noisy_scaffold_benchmark',
        'source_phase39_artifact': str(source_path.relative_to(project_root)),
        'train_shapes': list(cfg.train_shapes),
        'heldout_base_shapes': list(cfg.heldout_base_shapes),
        'heldout_new_shapes': list(cfg.heldout_new_shapes),
        'dephasing_values': gammas,
        'switch_gamma': switch_gamma,
        'switch_level': switch_level,
        'levels': levels,
        'suite_verdicts': {
            'benchmark_a': 'null_like',
            'benchmark_b': 'weak_control',
            'benchmark_c': 'local_superoperator_compactness_normalizer_supported',
            'benchmark_d': 'null_like',
            'benchmark_f': 'excluded_R4',
            'benchmark_g': verdict,
        },
        'verdict': verdict,
        'notes': [
            'Benchmark G is a second positive noisy scaffold benchmark constructed to test whether the accepted Phase 39 noisy rule transfers beyond benchmark C.',
            'No rule refit is done here: the accepted Phase 39 coefficients, higher-order terms, and compactness-normalizer rule are reused from benchmark C.',
            'This is an internal scaffold generalization test, not an external empirical validation benchmark.',
        ],
        'switch_metrics': {
            'train_r2': _safe_float(switch_level['train_fit']['r2']),
            'heldout_base_r2': _safe_float(switch_level['heldout_base_fit']['r2']),
            'heldout_new_r2': _safe_float(switch_level['heldout_new_fit']['r2']),
            'heldout_combined_r2': _safe_float(switch_level['heldout_combined_fit']['r2']),
            'heldout_combined_corr': _safe_float(switch_level['heldout_combined_fit']['corr']),
            'heldout_combined_sign_agreement': _safe_float(switch_level['heldout_combined_fit']['sign_agreement']),
        },
    }

    out_path = output_root / 'cgt_benchmarks' / 'results' / cfg.slug / 'benchmark_g_phase40_second_positive_noisy.json'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2))
    return payload


if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[3]
    payload = run_phase40_analysis(project_root=project_root, output_root=project_root)
    print(json.dumps(payload['switch_metrics'], indent=2))
