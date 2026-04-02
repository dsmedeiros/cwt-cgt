from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from ..benchmarks import get_benchmark
from ..continuation import continue_path_with_branch_ids
from ..lindblad import LindbladConfig, lindblad_branch_density, lindblad_superoperator, second_magnus_projection
from ..loop_protocols import build_loop_path, run_single_loop
from ..models import LoopConfig
from ..open_system import observable_operator


@dataclass(frozen=True)
class Phase24Config:
    benchmark_focus: str = 'benchmark_c'
    dephasing_values: tuple[float, ...] = (0.0, 0.10, 0.20, 0.30)
    train_shapes: tuple[str, ...] = ('square', 'circle')
    heldout_base_shapes: tuple[str, ...] = ('diamond', 'rounded_square')
    heldout_new_shapes: tuple[str, ...] = ('ellipse', 'stadium', 'hexagon')
    focus_max_centers: int = 2
    focus_max_side_lengths: int = 3
    steps_per_segment: int = 12
    default_switch_gamma: float = 0.30
    source_phase18_filename: str = 'benchmark_c_phase18_analytic_field.json'


def _load_zero_crossing(results_root: Path, benchmark_id: str, filename: str) -> float | None:
    benchmark = get_benchmark(benchmark_id)
    path = results_root / benchmark.slug / filename
    if not path.exists():
        return None
    payload = json.loads(path.read_text())
    zeros = payload.get('analytic_field', {}).get('zero_crossings', [])
    if not zeros:
        return None
    return float(np.mean([float(row['u_zero']) for row in zeros]))


def _fit_affine(rows: list[dict], feature_names: tuple[str, ...]) -> dict:
    trusted = [row for row in rows if row.get('trusted_pair')]
    if not trusted:
        return {'feature_names': list(feature_names), 'coefficients': {name: None for name in feature_names} | {'intercept': None}, 'predictions': [], 'fit': {'r2': None, 'corr': None, 'count': 0, 'sign_agreement': None}}
    X = np.asarray([[float(row[name]) for name in feature_names] + [1.0] for row in trusted], dtype=float)
    y = np.asarray([float(row['orientation_gap']) for row in trusted], dtype=float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    yhat = X @ beta
    ss = float(np.dot(y - float(np.mean(y)), y - float(np.mean(y))))
    r2 = None if ss <= 1e-15 else float(1.0 - np.dot(y - yhat, y - yhat) / ss)
    corr = None
    if len(y) >= 2 and not (np.allclose(y, y[0]) or np.allclose(yhat, yhat[0])):
        corr = float(np.corrcoef(y, yhat)[0, 1])
    sign_agreement = float(np.mean(np.sign(y) == np.sign(yhat))) if len(y) else None
    predictions = [float(val) for val in yhat]
    coefficients = {name: float(beta[idx]) for idx, name in enumerate(feature_names)}
    coefficients['intercept'] = float(beta[-1])
    return {
        'feature_names': list(feature_names),
        'coefficients': coefficients,
        'predictions': predictions,
        'fit': {'r2': r2, 'corr': corr, 'count': int(len(y)), 'sign_agreement': sign_agreement},
    }


def _apply_model(rows: list[dict], feature_names: tuple[str, ...], coefficients: dict[str, float | None]) -> list[dict]:
    out: list[dict] = []
    for row in rows:
        entry = dict(row)
        if row.get('trusted_pair'):
            pred = float(sum(float(coefficients[name]) * float(row[name]) for name in feature_names) + float(coefficients['intercept']))
            entry['predictor'] = pred
        else:
            entry['predictor'] = None
        out.append(entry)
    return out


def _summary(rows: list[dict], predictor_key: str = 'predictor') -> dict:
    trusted = [row for row in rows if row.get('trusted_pair') and row.get(predictor_key) is not None]
    if not trusted:
        return {'r2': None, 'corr': None, 'count': 0, 'sign_agreement': None}
    y = np.asarray([float(row['orientation_gap']) for row in trusted], dtype=float)
    yhat = np.asarray([float(row[predictor_key]) for row in trusted], dtype=float)
    ss = float(np.dot(y - float(np.mean(y)), y - float(np.mean(y))))
    r2 = None if ss <= 1e-15 else float(1.0 - np.dot(y - yhat, y - yhat) / ss)
    corr = None
    if len(y) >= 2 and not (np.allclose(y, y[0]) or np.allclose(yhat, yhat[0])):
        corr = float(np.corrcoef(y, yhat)[0, 1])
    sign_agreement = float(np.mean(np.sign(y) == np.sign(yhat))) if len(y) else None
    return {'r2': r2, 'corr': corr, 'count': int(len(y)), 'sign_agreement': sign_agreement}


def _run_loop_pair(benchmark_id: str, shape: str, center: tuple[float, float], side: float, gamma: float, steps_per_segment: int, zero_u: float | None, lind_cfg: LindbladConfig) -> dict:
    benchmark = get_benchmark(benchmark_id)
    loop_cfg = LoopConfig(shape=shape, steps_per_segment=steps_per_segment)
    ccw = run_single_loop(benchmark, center=center, side=side, orientation='ccw', config=loop_cfg)
    cw = run_single_loop(benchmark, center=center, side=side, orientation='cw', config=loop_cfg)
    trusted_pair = bool(ccw['trusted_r1'] and cw['trusted_r1'])
    row = {
        'shape': shape,
        'center': [float(center[0]), float(center[1])],
        'side_length': float(side),
        'dephasing': float(gamma),
        'trusted_pair': trusted_pair,
        'orientation_gap': None if not trusted_pair else float(ccw['response'] - cw['response']),
        'signed_flux_gap': None if not trusted_pair else float(ccw['signed_flux'] - cw['signed_flux']),
        'area_magnitude': float(abs(ccw['signed_area'])),
        'boundary_distance_u': None if zero_u is None else float(center[0] - zero_u),
    }
    if not trusted_pair:
        return row

    def _states(orientation: str):
        path = build_loop_path(center=center, side=side, orientation=orientation, shape=shape, steps_per_segment=steps_per_segment)
        cont = continue_path_with_branch_ids(benchmark=benchmark, path=path, config=loop_cfg)
        return cont['states']

    ccw_states = _states('ccw')
    cw_states = _states('cw')
    operator = observable_operator(benchmark, ccw_states[0])

    def _features(states: list) -> tuple[float, float]:
        supers = [lindblad_superoperator(state, lind_cfg, float(gamma)) for state in states]
        rho0 = lindblad_branch_density(states[0], lind_cfg, float(gamma))
        m2 = second_magnus_projection(supers, rho0, operator, lind_cfg.dt)
        if len(supers) >= 2:
            var_mean = float(np.mean([np.linalg.norm(supers[i + 1] - supers[i], ord='fro') for i in range(len(supers) - 1)]))
        else:
            var_mean = 0.0
        return float(m2), var_mean

    m2_ccw, var_ccw = _features(ccw_states)
    m2_cw, var_cw = _features(cw_states)
    m2_gap = float(m2_ccw - m2_cw)
    var_mean = float(0.5 * (var_ccw + var_cw))
    boundary = 0.0 if zero_u is None else float(center[0] - zero_u)
    row.update(
        {
            'm2_gap': m2_gap,
            'm2_gap_boundary': float(m2_gap * boundary),
            'generator_var_mean': var_mean,
            'm2_gap_var': float(m2_gap * var_mean),
            'm2_gap_boundary_var': float(m2_gap * boundary * var_mean),
        }
    )
    return row


def _plot_scatter(path: Path, train_rows: list[dict], held_rows: list[dict], higher_rows: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(7.0, 4.6))
    def _draw(rows: list[dict], label: str, marker: str):
        if not rows:
            return
        x = [float(row['predictor']) for row in rows if row.get('predictor') is not None]
        y = [float(row['orientation_gap']) for row in rows if row.get('predictor') is not None]
        if x:
            ax.scatter(x, y, label=label, marker=marker, alpha=0.85)
    _draw(train_rows, 'train (higher-order)', 'o')
    _draw(held_rows, 'held-out (higher-order)', 's')
    if higher_rows:
        x = np.asarray([float(row['predictor_baseline']) for row in higher_rows if row.get('predictor_baseline') is not None], dtype=float)
        y = np.asarray([float(row['orientation_gap']) for row in higher_rows if row.get('predictor_baseline') is not None], dtype=float)
        if x.size:
            ax.scatter(x, y, label='held-out (baseline)', marker='x', alpha=0.55)
    ax.set_title('Benchmark C: clean rerun higher-order predictor @ switch γ')
    ax.set_xlabel('Predicted orientation gap')
    ax.set_ylabel('Observed orientation gap')
    ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_r2_lines(path: Path, gammas: list[float], base_combined: list[float], higher_combined: list[float], base_new: list[float], higher_new: list[float]) -> None:
    fig, ax = plt.subplots(figsize=(7.0, 4.4))
    ax.plot(gammas, base_combined, marker='o', label='baseline held-out combined')
    ax.plot(gammas, higher_combined, marker='s', label='higher-order held-out combined')
    ax.plot(gammas, base_new, marker='^', label='baseline held-out new')
    ax.plot(gammas, higher_new, marker='d', label='higher-order held-out new')
    ax.set_title('Benchmark C: clean rerun held-out transfer vs dephasing')
    ax.set_xlabel('Dephasing γ')
    ax.set_ylabel('R²')
    ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_per_shape(path: Path, per_shape: dict[str, dict]) -> None:
    names = list(per_shape)
    baseline = [np.nan if per_shape[name]['baseline']['r2'] is None else float(per_shape[name]['baseline']['r2']) for name in names]
    higher = [np.nan if per_shape[name]['higher_order']['r2'] is None else float(per_shape[name]['higher_order']['r2']) for name in names]
    x = np.arange(len(names), dtype=float)
    width = 0.36
    fig, ax = plt.subplots(figsize=(8.0, 4.6))
    ax.bar(x - width / 2.0, baseline, width=width, label='baseline')
    ax.bar(x + width / 2.0, higher, width=width, label='higher-order')
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=20)
    ax.set_ylabel('R²')
    ax.set_title('Benchmark C: per-shape held-out transfer @ switch γ')
    ax.legend(loc='best')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def phase24_payload(project_root: Path, config: Phase24Config | None = None, lindblad_config: LindbladConfig | None = None) -> dict:
    cfg = config or Phase24Config()
    project_root = Path(project_root)
    results_root = project_root / 'cgt_benchmarks' / 'results'
    benchmark = get_benchmark(cfg.benchmark_focus)
    zero_u = _load_zero_crossing(results_root=results_root, benchmark_id=cfg.benchmark_focus, filename=cfg.source_phase18_filename)
    lind_cfg = lindblad_config or LindbladConfig(dephasing_values=tuple(float(x) for x in cfg.dephasing_values))

    centers = benchmark.default_loop_centers[: cfg.focus_max_centers]
    side_lengths = benchmark.default_loop_side_lengths[: cfg.focus_max_side_lengths]
    all_shapes = cfg.train_shapes + cfg.heldout_base_shapes + cfg.heldout_new_shapes

    levels: list[dict] = []
    gamma_values: list[float] = []
    base_combined_r2: list[float] = []
    higher_combined_r2: list[float] = []
    base_new_r2: list[float] = []
    higher_new_r2: list[float] = []

    baseline_features = ('m2_gap', 'm2_gap_boundary', 'area_magnitude')
    higher_features = ('m2_gap', 'm2_gap_boundary', 'area_magnitude', 'm2_gap_var', 'm2_gap_boundary_var')

    for gamma in cfg.dephasing_values:
        rows: list[dict] = []
        for shape in all_shapes:
            for center in centers:
                for side in side_lengths:
                    row = _run_loop_pair(
                        benchmark_id=cfg.benchmark_focus,
                        shape=shape,
                        center=center,
                        side=float(side),
                        gamma=float(gamma),
                        steps_per_segment=cfg.steps_per_segment,
                        zero_u=zero_u,
                        lind_cfg=lind_cfg,
                    )
                    row['family_group'] = 'train' if shape in cfg.train_shapes else ('heldout_base' if shape in cfg.heldout_base_shapes else 'heldout_new')
                    rows.append(row)

        train_rows = [row for row in rows if row['family_group'] == 'train' and row.get('trusted_pair')]
        held_base_rows = [row for row in rows if row['family_group'] == 'heldout_base' and row.get('trusted_pair')]
        held_new_rows = [row for row in rows if row['family_group'] == 'heldout_new' and row.get('trusted_pair')]
        held_all_rows = held_base_rows + held_new_rows

        baseline_fit = _fit_affine(train_rows, baseline_features)
        higher_fit = _fit_affine(train_rows, higher_features)

        baseline_rows = _apply_model(rows, baseline_features, baseline_fit['coefficients'])
        higher_rows = _apply_model(rows, higher_features, higher_fit['coefficients'])
        for base_row, high_row in zip(baseline_rows, higher_rows):
            high_row['predictor_baseline'] = base_row.get('predictor')

        switch_per_shape: dict[str, dict] = {}
        for shape in cfg.heldout_base_shapes + cfg.heldout_new_shapes:
            shape_base = [row for row in baseline_rows if row['shape'] == shape]
            shape_high = [row for row in higher_rows if row['shape'] == shape]
            switch_per_shape[shape] = {'baseline': _summary(shape_base), 'higher_order': _summary(shape_high)}

        level = {
            'dephasing': float(gamma),
            'zero_crossing_u_mean': zero_u,
            'baseline_model': {
                'feature_names': list(baseline_features),
                'coefficients': baseline_fit['coefficients'],
                'train_fit': _summary([row for row in baseline_rows if row['family_group'] == 'train']),
                'heldout_base_fit': _summary([row for row in baseline_rows if row['family_group'] == 'heldout_base']),
                'heldout_new_fit': _summary([row for row in baseline_rows if row['family_group'] == 'heldout_new']),
                'heldout_combined_fit': _summary([row for row in baseline_rows if row['family_group'] != 'train']),
            },
            'higher_order_model': {
                'feature_names': list(higher_features),
                'coefficients': higher_fit['coefficients'],
                'train_fit': _summary([row for row in higher_rows if row['family_group'] == 'train']),
                'heldout_base_fit': _summary([row for row in higher_rows if row['family_group'] == 'heldout_base']),
                'heldout_new_fit': _summary([row for row in higher_rows if row['family_group'] == 'heldout_new']),
                'heldout_combined_fit': _summary([row for row in higher_rows if row['family_group'] != 'train']),
            },
            'per_shape_fit': switch_per_shape,
            'rows': higher_rows,
        }
        levels.append(level)
        gamma_values.append(float(gamma))
        base_combined_r2.append(np.nan if level['baseline_model']['heldout_combined_fit']['r2'] is None else float(level['baseline_model']['heldout_combined_fit']['r2']))
        higher_combined_r2.append(np.nan if level['higher_order_model']['heldout_combined_fit']['r2'] is None else float(level['higher_order_model']['heldout_combined_fit']['r2']))
        base_new_r2.append(np.nan if level['baseline_model']['heldout_new_fit']['r2'] is None else float(level['baseline_model']['heldout_new_fit']['r2']))
        higher_new_r2.append(np.nan if level['higher_order_model']['heldout_new_fit']['r2'] is None else float(level['higher_order_model']['heldout_new_fit']['r2']))

    switch_level = min(levels, key=lambda row: abs(float(row['dephasing']) - cfg.default_switch_gamma))
    base_new = switch_level['baseline_model']['heldout_new_fit']['r2']
    higher_new = switch_level['higher_order_model']['heldout_new_fit']['r2']
    base_combined = switch_level['baseline_model']['heldout_combined_fit']['r2']
    higher_combined = switch_level['higher_order_model']['heldout_combined_fit']['r2']

    verdict = 'higher_order_generator_uncertain'
    if higher_new is not None and base_new is not None and float(higher_new) >= float(base_new) + 0.05:
        if higher_combined is not None and base_combined is not None and float(higher_combined) >= float(base_combined) - 0.01:
            verdict = 'higher_order_generator_new_family_improved_with_tradeoff'
        else:
            verdict = 'higher_order_generator_new_family_improved'
    elif higher_combined is not None and base_combined is not None and float(higher_combined) > float(base_combined) + 0.01:
        verdict = 'higher_order_generator_combined_improved'

    payload = {
        'phase': 'phase24_clean_rerun_higher_order_generator_transfer',
        'benchmark': cfg.benchmark_focus,
        'slug': benchmark.slug,
        'description': benchmark.description,
        'train_shapes': list(cfg.train_shapes),
        'heldout_base_shapes': list(cfg.heldout_base_shapes),
        'heldout_new_shapes': list(cfg.heldout_new_shapes),
        'dephasing_values': gamma_values,
        'switch_gamma': float(switch_level['dephasing']),
        'zero_crossing_u_mean': zero_u,
        'levels': levels,
        'switch_level': switch_level,
        'verdict': verdict,
        'suite_verdicts': {
            'benchmark_a': 'null_like (inherited)',
            'benchmark_b': 'weak_control (inherited)',
            'benchmark_c': verdict,
            'benchmark_d': 'null_like (inherited)',
            'benchmark_f': 'excluded_R4 (inherited)',
        },
        'notes': [
            'Phase 24 reruns the canonical and broadened held-out loop families from one current executable stack instead of mixing source rows across older artifacts.',
            'The baseline model is the clean generator-side affine rule on m2_gap, m2_gap_boundary, and area.',
            'The higher-order model adds generator-variation-weighted terms m2_gap_var and m2_gap_boundary_var, calibrated on canonical square/circle rows only and then transferred unchanged to all held-out families.',
        ],
    }

    bench_dir = results_root / benchmark.slug
    bench_dir.mkdir(parents=True, exist_ok=True)
    out_path = bench_dir / 'benchmark_c_phase24_clean_rerun_higher_order.json'
    out_path.write_text(json.dumps(payload, indent=2))

    plots_dir = project_root / 'cgt_benchmarks' / 'reports' / 'plots' / 'phase24_clean_rerun' / benchmark.slug
    train_rows = [row for row in switch_level['rows'] if row['family_group'] == 'train' and row.get('predictor') is not None]
    held_rows = [row for row in switch_level['rows'] if row['family_group'] != 'train' and row.get('predictor') is not None]
    _plot_scatter(plots_dir / 'response_vs_higher_order_predictor_switch.png', train_rows, held_rows, held_rows)
    _plot_r2_lines(plots_dir / 'heldout_r2_vs_dephasing.png', gamma_values, base_combined_r2, higher_combined_r2, base_new_r2, higher_new_r2)
    _plot_per_shape(plots_dir / 'per_shape_r2_switch.png', switch_level['per_shape_fit'])

    summary_path = project_root / 'cgt_benchmarks' / 'reports' / 'phase24_summary.json'
    summary_path.write_text(json.dumps(payload, indent=2))
    return payload
