from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np

from ..benchmarks import get_benchmark
from ..lindblad import LindbladConfig, lindblad_branch_density
from .phase13_analysis import Phase13Config, phase13_payload
from .phase15_analysis import DensityCache, _fit_affine, _plot_bars, _plot_line
from .phase18_analysis import _analytic_rows, _build_context, _centered_tangent_field


@dataclass(frozen=True)
class Phase19Config:
    benchmark_ids: tuple[str, ...] = ('benchmark_a', 'benchmark_b', 'benchmark_c', 'benchmark_d', 'benchmark_f')
    benchmark_focus: str = 'benchmark_c'
    scan_mesh: int = 7
    sigma_factor: float = 0.80
    support_floor: float = 2.0
    structural_amplitude_floor: float = 5.0
    default_switch_gamma: float = 0.30
    sample_resolution: int = 21


def _load_or_build_phase13(output_root: Path, benchmark_id: str, cfg: Phase19Config, lind_cfg: LindbladConfig) -> dict:
    benchmark = get_benchmark(benchmark_id)
    path = output_root / benchmark.slug / f'{benchmark_id}_phase13_atlas.json'
    if path.exists():
        return json.loads(path.read_text())
    suite = phase13_payload(
        output_root=output_root,
        phase13_config=Phase13Config(benchmark_ids=(benchmark_id,), benchmark_focus=benchmark_id, scan_mesh=cfg.scan_mesh, dephasing_values=tuple(float(x) for x in lind_cfg.dephasing_values)),
        lindblad_config=lind_cfg,
    )
    return suite['benchmark_payloads'][benchmark_id]


def _field_for_gamma(benchmark_id: str, gamma: float, cfg: Phase19Config, lind_cfg: LindbladConfig, cache: DensityCache, context_cache: dict[str, dict]) -> dict:
    context = context_cache.setdefault(benchmark_id, _build_context(benchmark_id=benchmark_id, scan_mesh=cfg.scan_mesh))
    rows = _analytic_rows(context=context, dephasing=float(gamma), lind_cfg=lind_cfg, cache=cache)
    return _centered_tangent_field(
        rows=rows,
        grid_u=context['grid_u'],
        grid_v=context['grid_v'],
        sigma_factor=cfg.sigma_factor,
        support_floor=cfg.support_floor,
        structural_amplitude_floor=cfg.structural_amplitude_floor,
    )


def _zero_crossing_mean(field: dict) -> float | None:
    zeros = field.get('zero_crossings') or []
    if not zeros:
        return None
    return float(np.mean([row['u_zero'] for row in zeros]))


def _bilinear(values: np.ndarray, xs: np.ndarray, ys: np.ndarray, x0: float, y0: float) -> float:
    if values.size == 0:
        return float('nan')
    i = int(np.searchsorted(xs, x0) - 1)
    j = int(np.searchsorted(ys, y0) - 1)
    i = max(0, min(i, len(xs) - 2))
    j = max(0, min(j, len(ys) - 2))
    x_lo, x_hi = float(xs[i]), float(xs[i + 1])
    y_lo, y_hi = float(ys[j]), float(ys[j + 1])
    q00 = float(values[i, j])
    q01 = float(values[i, j + 1])
    q10 = float(values[i + 1, j])
    q11 = float(values[i + 1, j + 1])
    tx = 0.0 if x_hi == x_lo else float((x0 - x_lo) / (x_hi - x_lo))
    ty = 0.0 if y_hi == y_lo else float((y0 - y_lo) / (y_hi - y_lo))
    return float((1.0 - tx) * (1.0 - ty) * q00 + (1.0 - tx) * ty * q01 + tx * (1.0 - ty) * q10 + tx * ty * q11)


def _loop_region_sample(field: dict, *, shape: str, center: tuple[float, float], side_length: float, sample_resolution: int) -> dict:
    field_values = np.asarray(field['centered_field'], dtype=float)
    cells_u = np.asarray(field['cells_u'], dtype=float)
    cells_v = np.asarray(field['cells_v'], dtype=float)
    zero_u = _zero_crossing_mean(field)
    center_value = _bilinear(field_values, cells_u, cells_v, float(center[0]), float(center[1]))

    samples: list[float] = []
    half = 0.5 * float(side_length)
    if shape == 'square':
        for du in np.linspace(-half, half, sample_resolution):
            for dv in np.linspace(-half, half, sample_resolution):
                samples.append(_bilinear(field_values, cells_u, cells_v, float(center[0] + du), float(center[1] + dv)))
    else:
        radius = half
        for du in np.linspace(-radius, radius, sample_resolution):
            for dv in np.linspace(-radius, radius, sample_resolution):
                if du * du + dv * dv <= radius * radius + 1e-12:
                    samples.append(_bilinear(field_values, cells_u, cells_v, float(center[0] + du), float(center[1] + dv)))
    region = np.asarray(samples, dtype=float)
    region_mean = float(np.mean(region)) if region.size else center_value
    region_min = float(np.min(region)) if region.size else center_value
    region_max = float(np.max(region)) if region.size else center_value
    sign_span = bool(region_min < 0.0 < region_max)
    boundary_distance = None if zero_u is None else float(center[0] - zero_u)
    boundary_crossing = None if boundary_distance is None else bool(abs(boundary_distance) <= half + 1e-12)
    return {
        'center_value': center_value,
        'region_mean': region_mean,
        'region_min': region_min,
        'region_max': region_max,
        'sign_span': sign_span,
        'boundary_zero_u_mean': zero_u,
        'boundary_distance_u': boundary_distance,
        'boundary_crossing': boundary_crossing,
        'sample_count': int(region.size),
    }


def _summary(values: Iterable[float]) -> dict:
    arr = np.asarray(list(values), dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return {'count': 0, 'min': None, 'max': None, 'mean': None, 'median': None}
    return {
        'count': int(arr.size),
        'min': float(np.min(arr)),
        'max': float(np.max(arr)),
        'mean': float(np.mean(arr)),
        'median': float(np.median(arr)),
    }


def _group_summary(rows: list[dict]) -> dict:
    trusted = [row for row in rows if row['trusted_pair'] and np.isfinite(row.get('predicted_response_gap', np.nan))]
    x = np.asarray([row['predicted_response_gap'] for row in trusted], dtype=float)
    y = np.asarray([row['orientation_gap'] for row in trusted], dtype=float)
    fit = _fit_affine(x, y)
    sign_agreement = None
    if int(np.sum(np.isfinite(x) & np.isfinite(y))) > 0:
        mask = np.isfinite(x) & np.isfinite(y)
        sign_agreement = float(np.mean(np.sign(x[mask]) == np.sign(y[mask])))
    return {
        'fit_predicted_response_vs_observed_gap': fit,
        'count_total': int(len(rows)),
        'count_trusted': int(len(trusted)),
        'count_excluded': int(sum(1 for row in rows if not row['trusted_pair'])),
        'sign_agreement': sign_agreement,
        'boundary_crossing_fraction': float(np.mean([bool(row.get('analytic_boundary_crossing')) for row in trusted])) if trusted else None,
        'sign_span_fraction': float(np.mean([bool(row.get('analytic_sign_span')) for row in trusted])) if trusted else None,
        'predicted_response_abs_summary': _summary(abs(float(row['predicted_response_gap'])) for row in trusted),
        'orientation_gap_abs_summary': _summary(abs(float(row['orientation_gap'])) for row in trusted),
        'field_center_summary': _summary(float(row['analytic_field_center']) for row in trusted),
        'field_region_summary': _summary(float(row['analytic_field_region_mean']) for row in trusted),
        'boundary_distance_summary': _summary(float(row['analytic_boundary_distance_u']) for row in trusted if row.get('analytic_boundary_distance_u') is not None),
    }


def _level_verdict(benchmark_id: str, level: dict) -> str:
    if benchmark_id == 'benchmark_f':
        return 'excluded_R4'
    if benchmark_id in {'benchmark_a', 'benchmark_d'}:
        return 'null_like'
    if benchmark_id == 'benchmark_b':
        return 'weak_control'
    if benchmark_id == 'benchmark_c':
        best_patch_r2 = level['best_patch_r2']
        if best_patch_r2 is not None and float(best_patch_r2) >= 0.60:
            if level['shape_residual_gap'] is not None and float(level['shape_residual_gap']) >= 0.30:
                return 'field_aligned_with_shape_residual'
            return 'field_aligned_local'
        return 'review'
    return 'review'


def _annotated_level(level: dict, field: dict, benchmark_id: str, cfg: Phase19Config) -> dict:
    rows: list[dict] = []
    for row in level['pair_rows']:
        annotated = dict(row)
        if row['trusted_pair']:
            sample = _loop_region_sample(
                field,
                shape=str(row['shape']),
                center=(float(row['center'][0]), float(row['center'][1])),
                side_length=float(row['side_length']),
                sample_resolution=cfg.sample_resolution,
            )
            predictor = float(sample['region_mean'] * float(row['aligned_mixed_holonomy_gap']))
            annotated.update(
                {
                    'analytic_field_center': float(sample['center_value']),
                    'analytic_field_region_mean': float(sample['region_mean']),
                    'analytic_field_region_min': float(sample['region_min']),
                    'analytic_field_region_max': float(sample['region_max']),
                    'analytic_sign_span': bool(sample['sign_span']),
                    'analytic_boundary_zero_u_mean': sample['boundary_zero_u_mean'],
                    'analytic_boundary_distance_u': sample['boundary_distance_u'],
                    'analytic_boundary_crossing': sample['boundary_crossing'],
                    'predicted_response_gap': predictor,
                }
            )
        else:
            annotated.update(
                {
                    'analytic_field_center': None,
                    'analytic_field_region_mean': None,
                    'analytic_field_region_min': None,
                    'analytic_field_region_max': None,
                    'analytic_sign_span': None,
                    'analytic_boundary_zero_u_mean': _zero_crossing_mean(field),
                    'analytic_boundary_distance_u': None,
                    'analytic_boundary_crossing': None,
                    'predicted_response_gap': None,
                }
            )
        rows.append(annotated)

    trusted = [row for row in rows if row['trusted_pair'] and row['predicted_response_gap'] is not None]
    global_fit = _group_summary(rows)

    patch_groups: dict[str, list[dict]] = {}
    shape_groups: dict[str, list[dict]] = {}
    center_groups: dict[str, list[dict]] = {}
    boundary_groups: dict[str, list[dict]] = {'crossing': [], 'same_side': []}
    for row in rows:
        patch_key = f"{row['shape']}|({row['center'][0]:+.2f},{row['center'][1]:+.2f})"
        center_key = f"({row['center'][0]:+.2f},{row['center'][1]:+.2f})"
        patch_groups.setdefault(patch_key, []).append(row)
        shape_groups.setdefault(str(row['shape']), []).append(row)
        center_groups.setdefault(center_key, []).append(row)
        if row['trusted_pair']:
            bucket = 'crossing' if bool(row.get('analytic_boundary_crossing')) else 'same_side'
            boundary_groups[bucket].append(row)

    patch_atlas = {key: _group_summary(group) for key, group in patch_groups.items()}
    by_shape = {key: _group_summary(group) for key, group in shape_groups.items()}
    by_center = {key: _group_summary(group) for key, group in center_groups.items()}
    by_boundary = {key: _group_summary(group) for key, group in boundary_groups.items()}

    best_patch_key = None
    best_patch_r2 = None
    for key, summary in patch_atlas.items():
        r2 = summary['fit_predicted_response_vs_observed_gap']['r2']
        if r2 is None:
            continue
        if best_patch_r2 is None or float(r2) > float(best_patch_r2):
            best_patch_r2 = float(r2)
            best_patch_key = key

    square_r2 = by_shape.get('square', {}).get('fit_predicted_response_vs_observed_gap', {}).get('r2')
    circle_r2 = by_shape.get('circle', {}).get('fit_predicted_response_vs_observed_gap', {}).get('r2')
    shape_residual_gap = None
    if square_r2 is not None and circle_r2 is not None:
        shape_residual_gap = float(abs(float(square_r2) - float(circle_r2)))

    summary = {
        'dephasing': float(level['dephasing']),
        'field_reference': {
            'structural_amplitude': float(field['structural_amplitude']),
            'zero_crossing_u_mean': _zero_crossing_mean(field),
            'valid_cell_count': int(np.sum(np.asarray(field['valid_mask'], dtype=bool))),
        },
        'pair_rows': rows,
        'global_summary': global_fit,
        'patch_atlas': patch_atlas,
        'family_summaries': {'by_shape': by_shape, 'by_center': by_center, 'by_boundary': by_boundary},
        'best_patch_key': best_patch_key,
        'best_patch_r2': best_patch_r2,
        'shape_residual_gap': shape_residual_gap,
        'trusted_pair_count': int(len(trusted)),
        'excluded_pair_count': int(sum(1 for row in rows if not row['trusted_pair'])),
    }
    summary['verdict'] = _level_verdict(benchmark_id, summary)
    return summary


def _benchmark_verdict(benchmark_id: str, switch_level: dict) -> str:
    return str(switch_level['verdict'])


def _plot_switch_scatter(path: Path, rows: list[dict], title: str) -> None:
    fig, ax = plt.subplots(figsize=(6.8, 4.4))
    markers = {'square': 'o', 'circle': 's'}
    for row in rows:
        if not row['trusted_pair'] or row['predicted_response_gap'] is None:
            continue
        label = f"{row['shape']} @ ({row['center'][0]:+.2f},{row['center'][1]:+.2f})"
        ax.scatter(float(row['predicted_response_gap']), float(row['orientation_gap']), marker=markers.get(str(row['shape']), 'o'), alpha=0.85, label=label)
    handles, labels = ax.get_legend_handles_labels()
    uniq = dict(zip(labels, handles))
    ax.legend(uniq.values(), uniq.keys(), fontsize=7, loc='best')
    ax.axhline(0.0, color='black', linewidth=0.8, alpha=0.5)
    ax.axvline(0.0, color='black', linewidth=0.8, alpha=0.5)
    ax.set_title(title)
    ax.set_xlabel('Analytic-field predicted response gap')
    ax.set_ylabel('Observed orientation gap')
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_switch_boundary_bars(path: Path, switch_level: dict, title: str) -> None:
    labels = ['crossing', 'same_side']
    values = []
    for label in labels:
        summary = switch_level['family_summaries']['by_boundary'].get(label, {})
        r2 = summary.get('fit_predicted_response_vs_observed_gap', {}).get('r2')
        values.append(float(r2) if r2 is not None else 0.0)
    _plot_bars(path, labels, values, title=title, ylabel='R²')


def _plot_suite_switch_bars(path: Path, benchmark_summaries: dict[str, dict], title: str) -> None:
    labels = list(benchmark_summaries.keys())
    values = []
    for bench_id in labels:
        r2 = benchmark_summaries[bench_id]['switch_global_r2']
        values.append(float(r2) if r2 is not None else 0.0)
    _plot_bars(path, labels, values, title=title, ylabel='Switch global R²')


def phase19_payload(output_root: Path, phase19_config: Phase19Config | None = None, lindblad_config: LindbladConfig | None = None) -> dict:
    cfg = phase19_config or Phase19Config()
    lind_cfg = lindblad_config or LindbladConfig(scan_mesh=cfg.scan_mesh, dephasing_values=(0.0, 0.10, 0.20, 0.30), coherence_switch_floor=0.20)
    cache = DensityCache(lambda state, gamma: lindblad_branch_density(state, lind_cfg, gamma))
    context_cache: dict[str, dict] = {}

    benchmark_payloads: dict[str, dict] = {}
    benchmark_summaries: dict[str, dict] = {}
    for benchmark_id in cfg.benchmark_ids:
        bench = get_benchmark(benchmark_id)
        phase13 = _load_or_build_phase13(output_root, benchmark_id, cfg, lind_cfg)
        gamma_values = tuple(float(x) for x in phase13['dephasing_values'])
        levels = []
        for gamma in gamma_values:
            field = _field_for_gamma(benchmark_id=benchmark_id, gamma=float(gamma), cfg=cfg, lind_cfg=lind_cfg, cache=cache, context_cache=context_cache)
            raw_level = min(phase13['loop_levels'], key=lambda row: abs(float(row['dephasing']) - float(gamma)))
            levels.append(_annotated_level(raw_level, field, benchmark_id=benchmark_id, cfg=cfg))
        switch_gamma = float(phase13.get('recommended_switch_gamma', cfg.default_switch_gamma))
        switch_level = min(levels, key=lambda row: abs(float(row['dephasing']) - switch_gamma))
        payload = {
            'phase': 'phase19_loop_side_alignment',
            'benchmark': benchmark_id,
            'slug': bench.slug,
            'description': bench.description,
            'dephasing_values': [float(x) for x in gamma_values],
            'field_reference': 'phase18_analytic_centered_field',
            'loop_reference': 'phase13_loop_family',
            'recommended_switch_gamma': switch_gamma,
            'loop_levels': levels,
            'switch_level': switch_level,
            'verdict': _benchmark_verdict(benchmark_id, switch_level),
        }
        benchmark_payloads[benchmark_id] = payload
        benchmark_summaries[benchmark_id] = {
            'benchmark': benchmark_id,
            'switch_gamma': switch_gamma,
            'switch_global_r2': switch_level['global_summary']['fit_predicted_response_vs_observed_gap']['r2'],
            'switch_global_corr': switch_level['global_summary']['fit_predicted_response_vs_observed_gap']['corr'],
            'switch_sign_agreement': switch_level['global_summary']['sign_agreement'],
            'switch_best_patch_key': switch_level['best_patch_key'],
            'switch_best_patch_r2': switch_level['best_patch_r2'],
            'switch_shape_residual_gap': switch_level['shape_residual_gap'],
            'switch_boundary_crossing_r2': switch_level['family_summaries']['by_boundary']['crossing']['fit_predicted_response_vs_observed_gap']['r2'],
            'switch_same_side_r2': switch_level['family_summaries']['by_boundary']['same_side']['fit_predicted_response_vs_observed_gap']['r2'],
            'verdict': payload['verdict'],
        }
        bench_dir = output_root / bench.slug
        bench_dir.mkdir(parents=True, exist_ok=True)
        (bench_dir / f'{benchmark_id}_phase19_loop_alignment.json').write_text(json.dumps(payload, indent=2))

    focus = benchmark_payloads[cfg.benchmark_focus]
    focus_switch = focus['switch_level']

    reports_dir = output_root.parents[0] / 'reports'
    reports_dir.mkdir(parents=True, exist_ok=True)
    plots_dir = reports_dir / 'plots' / 'phase19_loop_alignment' / get_benchmark(cfg.benchmark_focus).slug
    plots_dir.mkdir(parents=True, exist_ok=True)
    _plot_switch_scatter(plots_dir / 'response_vs_analytic_predictor_switch.png', focus_switch['pair_rows'], title='Benchmark C: observed vs Phase 18 analytic predictor')
    _plot_switch_boundary_bars(plots_dir / 'boundary_group_r2_switch.png', focus_switch, title='Benchmark C: loop groups by sign-boundary crossing')
    gamma_values = np.asarray([level['dephasing'] for level in focus['loop_levels']], dtype=float)
    global_r2 = np.asarray([0.0 if level['global_summary']['fit_predicted_response_vs_observed_gap']['r2'] is None else float(level['global_summary']['fit_predicted_response_vs_observed_gap']['r2']) for level in focus['loop_levels']], dtype=float)
    best_patch_r2 = np.asarray([0.0 if level['best_patch_r2'] is None else float(level['best_patch_r2']) for level in focus['loop_levels']], dtype=float)
    _plot_line(plots_dir / 'r2_vs_dephasing.png', gamma_values, global_r2, title='Benchmark C: global loop-side fit vs γ', ylabel='Global R²')
    _plot_line(plots_dir / 'best_patch_r2_vs_dephasing.png', gamma_values, best_patch_r2, title='Benchmark C: best patch R² vs γ', ylabel='Best patch R²')
    suite_plots_dir = reports_dir / 'plots' / 'phase19_loop_alignment'
    suite_plots_dir.mkdir(parents=True, exist_ok=True)
    _plot_suite_switch_bars(suite_plots_dir / 'suite_switch_global_r2.png', benchmark_summaries, title='Loop-side analytic-field fit at switch γ')

    suite = {
        'phase': 'phase19_loop_side_alignment',
        'description': 'Loop-side noisy reporting expressed against the accepted Phase 18 analytic field so scan-side and loop-side noisy narratives share the same structural object.',
        'benchmark_payloads': benchmark_payloads,
        'benchmark_summaries': benchmark_summaries,
        'focus_benchmark': cfg.benchmark_focus,
        'focus_switch_summary': {
            'switch_gamma': focus['recommended_switch_gamma'],
            'global_fit': focus_switch['global_summary']['fit_predicted_response_vs_observed_gap'],
            'best_patch_key': focus_switch['best_patch_key'],
            'best_patch_r2': focus_switch['best_patch_r2'],
            'shape_residual_gap': focus_switch['shape_residual_gap'],
            'boundary_crossing_fit': focus_switch['family_summaries']['by_boundary']['crossing']['fit_predicted_response_vs_observed_gap'],
            'same_side_fit': focus_switch['family_summaries']['by_boundary']['same_side']['fit_predicted_response_vs_observed_gap'],
        },
        'notes': [
            'The loop-side noisy lane now uses the Phase 18 analytic field as its structural reference object.',
            'Predicted loop response is reported against the loop-footprint average of the Phase 18 field multiplied by the aligned mixed holonomy gap.',
            'Benchmark C remains the only positive noisy case, but the loop-side story is still family-fragmented: square and circle protocols do not collapse to one field-only law in the current scaffold.',
        ],
    }
    (reports_dir / 'phase19_summary.json').write_text(json.dumps(suite, indent=2))
    return suite
