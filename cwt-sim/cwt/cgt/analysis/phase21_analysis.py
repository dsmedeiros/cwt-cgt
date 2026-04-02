from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from ..benchmarks import get_benchmark
from ..continuation import continue_path_with_branch_ids
from ..lindblad import LindbladConfig, loop_generator_gap
from ..loop_protocols import build_loop_path, run_single_loop
from ..models import LoopConfig


@dataclass(frozen=True)
class Phase21Config:
    benchmark_ids: tuple[str, ...] = ('benchmark_a', 'benchmark_b', 'benchmark_c', 'benchmark_d', 'benchmark_f')
    benchmark_focus: str = 'benchmark_c'
    dephasing_values: tuple[float, ...] = (0.0, 0.10, 0.20, 0.30)
    train_shapes: tuple[str, ...] = ('square', 'circle')
    heldout_shapes: tuple[str, ...] = ('diamond', 'rounded_square')
    default_switch_gamma: float = 0.30
    focus_max_centers: int = 2
    focus_max_side_lengths: int = 3
    default_steps_per_segment: int = 12
    focus_steps_per_segment: int = 8


def _steps_for_benchmark(benchmark_id: str, cfg: Phase21Config) -> int:
    return cfg.focus_steps_per_segment if benchmark_id == cfg.benchmark_focus else cfg.default_steps_per_segment


def _load_phase18_zero_crossing(output_root: Path, benchmark_id: str) -> float | None:
    benchmark = get_benchmark(benchmark_id)
    path = output_root / benchmark.slug / f'{benchmark_id}_phase18_analytic_field.json'
    if not path.exists():
        return None
    payload = json.loads(path.read_text())
    field = payload.get('analytic_field', {})
    crossings = field.get('zero_crossings') or []
    zeros = [float(item['u_zero']) for item in crossings if item.get('u_zero') is not None]
    if not zeros:
        return None
    return float(np.mean(zeros))


def _fit_affine(x: np.ndarray, y: np.ndarray) -> dict:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    if int(np.sum(mask)) < 2:
        return {'slope': None, 'intercept': None, 'r2': None, 'corr': None, 'count': int(np.sum(mask))}
    x = x[mask]
    y = y[mask]
    X = np.column_stack([x, np.ones_like(x)])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    yhat = X @ beta
    ss = float(np.dot(y - float(np.mean(y)), y - float(np.mean(y))))
    r2 = None if ss <= 1e-15 else float(1.0 - np.dot(y - yhat, y - yhat) / ss)
    corr = None
    if len(y) >= 2 and not (np.allclose(yhat, yhat[0]) or np.allclose(y, y[0])):
        corr = float(np.corrcoef(y, yhat)[0, 1])
    return {'slope': float(beta[0]), 'intercept': float(beta[1]), 'r2': r2, 'corr': corr, 'count': int(len(y))}


def _fit_multifeature(rows: list[dict]) -> dict:
    if not rows:
        return {
            'coefficients': {'path_gap': None, 'path_gap_boundary_distance': None, 'area_magnitude': None, 'intercept': None},
            'predictions': [],
            'fit': {'r2': None, 'corr': None, 'count': 0},
        }
    x1 = np.asarray([float(row['path_gap']) for row in rows], dtype=float)
    x2 = np.asarray([float(row['path_gap_boundary_distance']) for row in rows], dtype=float)
    x3 = np.asarray([float(row['area_magnitude']) for row in rows], dtype=float)
    y = np.asarray([float(row['orientation_gap']) for row in rows], dtype=float)
    mask = np.isfinite(x1) & np.isfinite(x2) & np.isfinite(x3) & np.isfinite(y)
    if int(np.sum(mask)) < 4:
        return {
            'coefficients': {'path_gap': None, 'path_gap_boundary_distance': None, 'area_magnitude': None, 'intercept': None},
            'predictions': [None for _ in rows],
            'fit': {'r2': None, 'corr': None, 'count': int(np.sum(mask))},
        }
    X = np.column_stack([x1[mask], x2[mask], x3[mask], np.ones(int(np.sum(mask)), dtype=float)])
    beta, *_ = np.linalg.lstsq(X, y[mask], rcond=None)
    yhat = X @ beta
    preds = np.full_like(y, np.nan)
    preds[mask] = yhat
    ss = float(np.dot(y[mask] - float(np.mean(y[mask])), y[mask] - float(np.mean(y[mask]))))
    r2 = None if ss <= 1e-15 else float(1.0 - np.dot(y[mask] - yhat, y[mask] - yhat) / ss)
    corr = None
    if int(np.sum(mask)) >= 2 and not (np.allclose(yhat, yhat[0]) or np.allclose(y[mask], y[mask][0])):
        corr = float(np.corrcoef(y[mask], yhat)[0, 1])
    return {
        'coefficients': {
            'path_gap': float(beta[0]),
            'path_gap_boundary_distance': float(beta[1]),
            'area_magnitude': float(beta[2]),
            'intercept': float(beta[3]),
        },
        'predictions': [None if not np.isfinite(val) else float(val) for val in preds],
        'fit': {'r2': r2, 'corr': corr, 'count': int(np.sum(mask))},
    }


def _prediction_summary(rows: list[dict], key: str) -> dict:
    trusted = [row for row in rows if row.get(key) is not None]
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


def _run_loop_pair(benchmark_id: str, shape: str, center: tuple[float, float], side: float, gamma: float, steps_per_segment: int, lind_cfg: LindbladConfig) -> dict:
    benchmark = get_benchmark(benchmark_id)
    loop_cfg = LoopConfig(shape=shape, steps_per_segment=steps_per_segment)
    ccw = run_single_loop(benchmark, center=center, side=side, orientation='ccw', config=loop_cfg)
    cw = run_single_loop(benchmark, center=center, side=side, orientation='cw', config=loop_cfg)
    if not (ccw['trusted_r1'] and cw['trusted_r1']):
        return {
            'shape': shape,
            'center': [float(center[0]), float(center[1])],
            'side_length': float(side),
            'dephasing': float(gamma),
            'trusted_pair': False,
            'orientation_gap': None,
        }
    ccw_path = build_loop_path(center=center, side=side, orientation='ccw', shape=shape, steps_per_segment=steps_per_segment)
    cw_path = build_loop_path(center=center, side=side, orientation='cw', shape=shape, steps_per_segment=steps_per_segment)
    ccw_cont = continue_path_with_branch_ids(benchmark=benchmark, path=ccw_path, config=loop_cfg)
    cw_cont = continue_path_with_branch_ids(benchmark=benchmark, path=cw_path, config=loop_cfg)
    path_gap = loop_generator_gap(ccw_states=ccw_cont['states'], cw_states=cw_cont['states'], benchmark=benchmark, config=lind_cfg, dephasing=float(gamma))
    return {
        'shape': shape,
        'center': [float(center[0]), float(center[1])],
        'side_length': float(side),
        'dephasing': float(gamma),
        'trusted_pair': True,
        'orientation_gap': float(ccw['response'] - cw['response']),
        'response_sign_reversed': bool(np.sign(ccw['response']) == -np.sign(cw['response']) and (abs(ccw['response']) > 1e-12 or abs(cw['response']) > 1e-12)),
        'signed_flux_gap': float(ccw['signed_flux'] - cw['signed_flux']),
        'path_gap': float(path_gap),
        'area_magnitude': float(abs(ccw['signed_area'])),
        'ccw': ccw,
        'cw': cw,
    }


def phase21_payload(output_root: Path, phase21_config: Phase21Config | None = None, lindblad_config: LindbladConfig | None = None) -> dict:
    cfg = phase21_config or Phase21Config()
    lind_cfg = lindblad_config or LindbladConfig(dephasing_values=tuple(float(x) for x in cfg.dephasing_values))
    output_root = Path(output_root)
    benchmark_payloads: dict[str, dict] = {}
    benchmark_summaries: dict[str, dict] = {}

    for benchmark_id in cfg.benchmark_ids:
        benchmark = get_benchmark(benchmark_id)
        if benchmark.expected_regime == 'R4':
            payload = {
                'phase': 'phase21_generator_shape_transfer',
                'benchmark': benchmark_id,
                'slug': benchmark.slug,
                'description': benchmark.description,
                'verdict': 'excluded_R4',
                'reason': 'Explicit switching benchmark; held-out noisy loop transfer is not evaluated on excluded R4 families.',
            }
            benchmark_payloads[benchmark_id] = payload
            benchmark_summaries[benchmark_id] = {'benchmark': benchmark_id, 'verdict': 'excluded_R4', 'heldout_r2_switch': None}
            continue

        zero_u = _load_phase18_zero_crossing(output_root, benchmark_id)
        steps = _steps_for_benchmark(benchmark_id, cfg)
        centers = benchmark.default_loop_centers[: cfg.focus_max_centers]
        side_lengths = benchmark.default_loop_side_lengths[: cfg.focus_max_side_lengths]

        all_rows: list[dict] = []
        levels: list[dict] = []
        for gamma in cfg.dephasing_values:
            rows: list[dict] = []
            for shape in cfg.train_shapes + cfg.heldout_shapes:
                for center in centers:
                    for side in side_lengths:
                        row = _run_loop_pair(benchmark_id, shape, center, float(side), float(gamma), steps, lind_cfg)
                        if row['trusted_pair']:
                            dist = 0.0 if zero_u is None else float(center[0] - zero_u)
                            row['boundary_distance_u'] = None if zero_u is None else dist
                            row['path_gap_boundary_distance'] = float(row['path_gap'] * dist)
                            row['family_group'] = 'train' if shape in cfg.train_shapes else 'heldout'
                        else:
                            row['boundary_distance_u'] = None if zero_u is None else float(center[0] - zero_u)
                            row['path_gap_boundary_distance'] = None
                            row['family_group'] = 'train' if shape in cfg.train_shapes else 'heldout'
                        rows.append(row)
            train_rows = [row for row in rows if row['trusted_pair'] and row['family_group'] == 'train']
            held_rows = [row for row in rows if row['trusted_pair'] and row['family_group'] == 'heldout']
            fit = _fit_multifeature(train_rows)
            trusted_rows = [row for row in rows if row['trusted_pair']]
            trusted_preds = [pred for row, pred in zip(train_rows, fit['predictions'][: len(train_rows)])]
            # assign train predictions
            pred_iter = iter(fit['predictions'])
            assigned_rows = []
            for row in train_rows:
                row = dict(row)
                row['corrected_predictor'] = next(pred_iter)
                assigned_rows.append(row)
            coeffs = fit['coefficients']
            # evaluate held-out with training coefficients
            held_assigned: list[dict] = []
            for row in held_rows:
                pred = (
                    coeffs['path_gap'] * float(row['path_gap'])
                    + coeffs['path_gap_boundary_distance'] * float(row['path_gap_boundary_distance'])
                    + coeffs['area_magnitude'] * float(row['area_magnitude'])
                    + coeffs['intercept']
                )
                row = dict(row)
                row['corrected_predictor'] = float(pred)
                held_assigned.append(row)
            combined_rows = assigned_rows + held_assigned
            level = {
                'dephasing': float(gamma),
                'zero_crossing_u_mean': zero_u,
                'coefficients': coeffs,
                'train_fit': _prediction_summary(assigned_rows, 'corrected_predictor'),
                'heldout_fit': _prediction_summary(held_assigned, 'corrected_predictor'),
                'all_fit': _prediction_summary(combined_rows, 'corrected_predictor'),
                'shape_counts': {
                    'train': int(len(assigned_rows)),
                    'heldout': int(len(held_assigned)),
                },
                'pair_rows': rows,
                'annotated_rows': combined_rows,
            }
            levels.append(level)
            all_rows.extend(combined_rows)

        switch_level = min(levels, key=lambda row: abs(float(row['dephasing']) - cfg.default_switch_gamma))
        switch_heldout_r2 = switch_level['heldout_fit']['r2']
        if benchmark_id == cfg.benchmark_focus and switch_heldout_r2 is not None and float(switch_heldout_r2) >= 0.90:
            verdict = 'heldout_generator_generalized'
        elif benchmark_id == cfg.benchmark_focus and switch_heldout_r2 is not None and float(switch_heldout_r2) >= 0.50:
            verdict = 'heldout_generator_partial'
        elif benchmark_id in {'benchmark_a', 'benchmark_d'}:
            verdict = 'null_like'
        else:
            verdict = 'weak_control'

        payload = {
            'phase': 'phase21_generator_shape_transfer',
            'benchmark': benchmark_id,
            'slug': benchmark.slug,
            'description': benchmark.description,
            'train_shapes': list(cfg.train_shapes),
            'heldout_shapes': list(cfg.heldout_shapes),
            'dephasing_values': [float(x) for x in cfg.dephasing_values],
            'switch_gamma': float(switch_level['dephasing']),
            'zero_crossing_u_mean': zero_u,
            'levels': levels,
            'switch_level': switch_level,
            'verdict': verdict,
            'notes': [
                'Coefficients are calibrated on canonical square/circle loops only and then transferred unchanged to held-out diamond/rounded-square loops.',
                'The accepted scan-side reference object remains the Phase 18 analytic field; only its sign-boundary location enters this loop-side transfer model.',
            ],
        }
        benchmark_payloads[benchmark_id] = payload
        benchmark_summaries[benchmark_id] = {
            'benchmark': benchmark_id,
            'verdict': verdict,
            'switch_gamma': float(switch_level['dephasing']),
            'train_r2_switch': switch_level['train_fit']['r2'],
            'heldout_r2_switch': switch_level['heldout_fit']['r2'],
            'heldout_corr_switch': switch_level['heldout_fit']['corr'],
            'train_count_switch': switch_level['train_fit']['count'],
            'heldout_count_switch': switch_level['heldout_fit']['count'],
        }
        bench_dir = output_root / benchmark.slug
        bench_dir.mkdir(parents=True, exist_ok=True)
        (bench_dir / f'{benchmark_id}_phase21_heldout_shape_transfer.json').write_text(json.dumps(payload, indent=2))

    reports_dir = output_root.parents[0] / 'reports'
    reports_dir.mkdir(parents=True, exist_ok=True)
    plots_dir = reports_dir / 'plots' / 'phase21_heldout_transfer' / get_benchmark(cfg.benchmark_focus).slug
    plots_dir.mkdir(parents=True, exist_ok=True)

    focus = benchmark_payloads[cfg.benchmark_focus]
    switch = focus['switch_level']
    train_rows = [row for row in switch['annotated_rows'] if row['family_group'] == 'train']
    held_rows = [row for row in switch['annotated_rows'] if row['family_group'] == 'heldout']

    plt.figure(figsize=(6, 4))
    if train_rows:
        plt.scatter([float(row['corrected_predictor']) for row in train_rows], [float(row['orientation_gap']) for row in train_rows], label='train')
    if held_rows:
        plt.scatter([float(row['corrected_predictor']) for row in held_rows], [float(row['orientation_gap']) for row in held_rows], label='held-out')
    plt.xlabel('Corrected predictor')
    plt.ylabel('Observed orientation gap')
    plt.title('Benchmark C: response vs generator-corrected predictor')
    if train_rows or held_rows:
        plt.legend()
    plt.tight_layout()
    plt.savefig(plots_dir / 'response_vs_corrected_predictor_switch.png', dpi=180)
    plt.close()

    plt.figure(figsize=(6, 4))
    gammas = [float(level['dephasing']) for level in focus['levels']]
    train_r2 = [np.nan if level['train_fit']['r2'] is None else float(level['train_fit']['r2']) for level in focus['levels']]
    held_r2 = [np.nan if level['heldout_fit']['r2'] is None else float(level['heldout_fit']['r2']) for level in focus['levels']]
    plt.plot(gammas, train_r2, marker='o', label='train')
    plt.plot(gammas, held_r2, marker='o', label='held-out')
    plt.xlabel('Dephasing γ')
    plt.ylabel('R²')
    plt.title('Benchmark C: canonical vs held-out shape transfer')
    plt.legend()
    plt.tight_layout()
    plt.savefig(plots_dir / 'train_vs_heldout_r2.png', dpi=180)
    plt.close()

    plt.figure(figsize=(6, 4))
    shape_names = list(cfg.train_shapes + cfg.heldout_shapes)
    shape_vals = []
    rows = switch['annotated_rows']
    for shape in shape_names:
        subset = [row for row in rows if row['shape'] == shape and row.get('corrected_predictor') is not None]
        summary = _prediction_summary(subset, 'corrected_predictor')
        shape_vals.append(np.nan if summary['r2'] is None else float(summary['r2']))
    plt.bar(shape_names, shape_vals)
    plt.ylabel('R²')
    plt.title('Benchmark C: per-shape fit at switch γ')
    plt.tight_layout()
    plt.savefig(plots_dir / 'per_shape_r2_switch.png', dpi=180)
    plt.close()

    suite = {
        'phase': 'phase21_generator_shape_transfer',
        'description': 'Generator-side loop correction trained on canonical square/circle families and transferred unchanged to held-out diamond/rounded-square loop families.',
        'benchmark_payloads': benchmark_payloads,
        'benchmark_summaries': benchmark_summaries,
        'focus_benchmark': cfg.benchmark_focus,
        'focus_switch_summary': benchmark_summaries[cfg.benchmark_focus],
        'notes': [
            'This phase keeps the scan-side Phase 18 field fixed and tests loop-side generalization on held-out families.',
            'The correction coefficients are still calibrated, but only on canonical shapes; held-out transfer is now the main acceptance gate.',
        ],
    }
    (reports_dir / 'phase21_summary.json').write_text(json.dumps(suite, indent=2))
    return suite
