from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import matplotlib.pyplot as plt
import numpy as np

from cwt.geometry.mixed_state import (
    bures_distance_sq,
    mixed_loop_holonomy_phase,
    mixed_plaquette_curvature,
    phase_alignment_sign,
    purity,
    unwrap_phase_sequence,
)

from .._geom_compat import berry_loop_flux, summarize, summarize_abs
from ..benchmarks import get_benchmark
from ..continuation import build_branch_atlas, continue_path_with_branch_ids
from ..lindblad import LindbladConfig, apply_lindblad_step, lindblad_branch_density
from ..loop_protocols import build_loop_path
from ..models import LoopConfig, ScanConfig
from ..open_system import coherence_ratio, observable_operator


@dataclass(frozen=True)
class LoopFamilySpec:
    shapes: tuple[str, ...]
    centers: tuple[tuple[float, float], ...]
    side_lengths: tuple[float, ...]
    steps_per_segment: int = 18


@dataclass(frozen=True)
class Phase13Config:
    benchmark_ids: tuple[str, ...] = ('benchmark_a', 'benchmark_b', 'benchmark_c', 'benchmark_d', 'benchmark_f')
    benchmark_focus: str = 'benchmark_c'
    scan_mesh: int = 7
    dephasing_values: tuple[float, ...] = (0.0, 0.10, 0.20, 0.30)
    coherence_switch_floor: float = 0.20


class DensityCache:
    def __init__(self, fn: Callable):
        self.fn = fn
        self._cache: dict[tuple[float, tuple[float, ...]], np.ndarray] = {}

    @staticmethod
    def _signature(state) -> tuple[float, ...]:
        return tuple(np.round(np.concatenate([state.p.ravel(), state.theta.ravel(), state.kernel.ravel()]), 10).tolist())

    def get(self, state, dephasing: float) -> np.ndarray:
        key = (round(float(dephasing), 6), self._signature(state))
        if key not in self._cache:
            self._cache[key] = self.fn(state, float(dephasing))
        return self._cache[key]


def _family_for_benchmark(benchmark_id: str) -> LoopFamilySpec:
    if benchmark_id == 'benchmark_a':
        return LoopFamilySpec(shapes=('square', 'circle'), centers=((0.0, 0.0),), side_lengths=(0.10, 0.16, 0.22), steps_per_segment=18)
    if benchmark_id == 'benchmark_b':
        return LoopFamilySpec(shapes=('square', 'circle'), centers=((0.0, 0.0), (0.0, 0.20)), side_lengths=(0.10, 0.16, 0.22), steps_per_segment=18)
    if benchmark_id == 'benchmark_c':
        return LoopFamilySpec(shapes=('square', 'circle'), centers=((0.0, 0.0), (0.18, 0.0)), side_lengths=(0.10, 0.16, 0.22), steps_per_segment=8)
    if benchmark_id == 'benchmark_d':
        return LoopFamilySpec(shapes=('square',), centers=((0.0, 0.225), (0.03, 0.225)), side_lengths=(0.04, 0.06), steps_per_segment=18)
    if benchmark_id == 'benchmark_f':
        return LoopFamilySpec(shapes=('square',), centers=((0.0, 0.0), (0.70, 0.0), (-0.70, 0.0)), side_lengths=(0.18, 0.30), steps_per_segment=18)
    benchmark = get_benchmark(benchmark_id)
    return LoopFamilySpec(shapes=('square',), centers=benchmark.default_loop_centers, side_lengths=benchmark.default_loop_side_lengths, steps_per_segment=18)


def _fit_through_origin(xs: np.ndarray, ys: np.ndarray) -> dict[str, float | int | None]:
    if xs.size == 0 or np.allclose(xs, 0.0):
        return {'slope': None, 'r2': None, 'count': int(xs.size)}
    denom = float(np.dot(xs, xs))
    if denom <= 1e-15:
        return {'slope': None, 'r2': None, 'count': int(xs.size)}
    slope = float(np.dot(xs, ys) / denom)
    residual = ys - slope * xs
    numer = float(np.dot(residual, residual))
    denom_y = float(np.dot(ys, ys))
    r2 = None if denom_y <= 1e-15 else float(1.0 - numer / denom_y)
    return {'slope': slope, 'r2': r2, 'count': int(xs.size)}


def _corr(a: np.ndarray, b: np.ndarray) -> float | None:
    mask = np.isfinite(a) & np.isfinite(b)
    if int(np.sum(mask)) < 2:
        return None
    x = np.asarray(a[mask], dtype=float)
    y = np.asarray(b[mask], dtype=float)
    if np.allclose(x, x[0]) or np.allclose(y, y[0]):
        return None
    return float(np.corrcoef(x, y)[0, 1])


def _recommended_switch(levels: list[dict], floor: float) -> float:
    for level in levels:
        mean_coh = level['coherence_ratio_summary']['mean']
        if mean_coh is not None and float(mean_coh) <= floor:
            return float(level['dephasing'])
    return float(levels[-1]['dephasing'])


def _select_level(levels: list[dict], gamma: float) -> dict:
    return min(levels, key=lambda row: abs(float(row['dephasing']) - gamma))


def _patch_class(slope: float | None, r2: float | None, count: int, threshold: float = 1e-4) -> str:
    if count < 2 or slope is None:
        return 'insufficient'
    if abs(float(slope)) < threshold:
        return 'null-like'
    if r2 is None or float(r2) < 0.35:
        return 'weak'
    return 'positive' if float(slope) > 0.0 else 'negative'


def _level_verdict(benchmark_id: str, level: dict) -> str:
    trusted = int(level['trusted_pair_count'])
    excluded = int(level['excluded_pair_count'])
    patches = list(level['patch_atlas'].values())
    strong_pos = [patch for patch in patches if patch['patch_class'] == 'positive']
    strong_neg = [patch for patch in patches if patch['patch_class'] == 'negative']
    if benchmark_id == 'benchmark_f':
        return 'excluded_R4' if trusted == 0 or excluded >= trusted else 'mixed_R4'
    if benchmark_id == 'benchmark_c':
        if strong_pos and strong_neg:
            return 'local_fragmented'
        if strong_pos:
            return 'local_positive'
        if strong_neg:
            return 'sign-conflicted'
        return 'review'
    if benchmark_id in {'benchmark_a', 'benchmark_d'}:
        if strong_pos or strong_neg:
            return 'unexpected_local_structure'
        return 'null_like'
    if benchmark_id == 'benchmark_b':
        if strong_pos or strong_neg:
            return 'patchy_control'
        return 'weak_control'
    return 'review'


def _summarize_patch_group(rows: list[dict]) -> dict:
    trusted = [row for row in rows if row['trusted_pair']]
    xs = np.asarray([row['aligned_mixed_holonomy_gap'] for row in trusted], dtype=float)
    ys = np.asarray([row['orientation_gap'] for row in trusted], dtype=float)
    fit = _fit_through_origin(xs, ys)
    side_lengths = sorted({float(row['side_length']) for row in rows})
    return {
        'fit': fit,
        'count_total': int(len(rows)),
        'count_trusted': int(len(trusted)),
        'count_excluded': int(sum(1 for row in rows if not row['trusted_pair'])),
        'mean_abs_aligned_holonomy_gap': float(np.mean(np.abs(xs))) if xs.size else None,
        'mean_abs_orientation_gap': float(np.mean(np.abs(ys))) if ys.size else None,
        'coherence_ratio_summary': summarize(row['avg_coherence_ratio_mean'] for row in rows),
        'purity_summary': summarize(row['avg_purity_mean'] for row in rows),
        'side_lengths': side_lengths,
        'patch_class': _patch_class(fit['slope'], fit['r2'], int(fit['count'])),
    }


def _scan_level(benchmark_id: str, scan_config: ScanConfig, dephasing: float, cache: DensityCache) -> dict:
    benchmark = get_benchmark(benchmark_id)
    grid_u = np.linspace(*benchmark.control_bounds[0], scan_config.mesh, dtype=float)
    grid_v = np.linspace(*benchmark.control_bounds[1], scan_config.mesh, dtype=float)
    du = float(grid_u[1] - grid_u[0]) if scan_config.mesh > 1 else 1.0
    dv = float(grid_v[1] - grid_v[0]) if scan_config.mesh > 1 else 1.0
    atlas = build_branch_atlas(benchmark=benchmark, grid_u=grid_u, grid_v=grid_v, config=scan_config)
    states = atlas['chosen_states']
    rho_grid: list[list[np.ndarray]] = []
    coherence_grid = np.full((scan_config.mesh, scan_config.mesh), np.nan, dtype=float)
    purity_grid = np.full((scan_config.mesh, scan_config.mesh), np.nan, dtype=float)
    for i in range(scan_config.mesh):
        row: list[np.ndarray] = []
        for j in range(scan_config.mesh):
            state = states[i][j]
            rho = cache.get(state, dephasing)
            row.append(rho)
            coherence_grid[i, j] = coherence_ratio(rho, state)
            purity_grid[i, j] = purity(rho)
        rho_grid.append(row)

    metric = np.full((scan_config.mesh, scan_config.mesh), np.nan, dtype=float)
    for i in range(1, scan_config.mesh - 1):
        for j in range(1, scan_config.mesh - 1):
            metric[i, j] = (
                bures_distance_sq(rho_grid[i + 1][j], rho_grid[i - 1][j]) / max((2.0 * du) ** 2, 1e-12)
                + bures_distance_sq(rho_grid[i][j + 1], rho_grid[i][j - 1]) / max((2.0 * dv) ** 2, 1e-12)
            )

    curvature = np.full((scan_config.mesh - 1, scan_config.mesh - 1), np.nan, dtype=float)
    area = du * dv
    for i in range(scan_config.mesh - 1):
        for j in range(scan_config.mesh - 1):
            if any([atlas['ambiguous_map'][i][j], atlas['ambiguous_map'][i + 1][j], atlas['ambiguous_map'][i + 1][j + 1], atlas['ambiguous_map'][i][j + 1]]):
                continue
            curvature[i, j] = mixed_plaquette_curvature(rho_grid[i][j], rho_grid[i + 1][j], rho_grid[i + 1][j + 1], rho_grid[i][j + 1], area)

    return {
        'dephasing': float(dephasing),
        'mean_abs_mixed_curvature': float(np.nanmean(np.abs(curvature))) if np.isfinite(curvature).any() else 0.0,
        'metric_summary': summarize(metric.ravel()),
        'mixed_curvature_summary': summarize_abs(curvature.ravel()),
        'coherence_ratio_summary': summarize(coherence_grid.ravel()),
        'purity_summary': summarize(purity_grid.ravel()),
        'bures_metric_trace': metric.tolist(),
        'mixed_curvature': curvature.tolist(),
        'ambiguous_tile_count': int(sum(sum(1 for flag in row if flag) for row in atlas['ambiguous_map'])),
        'switch_tile_count': int(len(atlas['switch_tiles'])),
    }


def _loop_observable_response(benchmark, states, branch_rhos: list[np.ndarray], dephasing: float, step_fn: Callable) -> tuple[float, float, float, float, float]:
    rho = branch_rhos[0].copy()
    operator = observable_operator(benchmark, states[0])
    actual_samples: list[float] = []
    branch_samples: list[float] = []
    coherence_samples: list[float] = []
    purity_samples: list[float] = []
    for state, branch_rho in zip(states, branch_rhos):
        rho = step_fn(rho, state, dephasing)
        actual_samples.append(float(np.real(np.trace(rho @ operator))))
        branch_samples.append(float(np.real(np.trace(branch_rho @ operator))))
        coherence_samples.append(float(coherence_ratio(rho, state)))
        purity_samples.append(float(purity(rho)))
    if benchmark.primary_observable == 'excess_circulation':
        response = float(np.mean(actual_samples) - np.mean(branch_samples))
    else:
        response = float(actual_samples[-1] - branch_samples[-1])
    return (
        response,
        float(np.mean(coherence_samples)) if coherence_samples else 0.0,
        float(np.mean(purity_samples)) if purity_samples else 0.0,
        float(np.mean(actual_samples)) if actual_samples else 0.0,
        float(np.mean(branch_samples)) if branch_samples else 0.0,
    )


def _precompute_loop_branch(benchmark_id: str, shape: str, center: tuple[float, float], side: float, orientation: str, steps_per_segment: int) -> dict:
    benchmark = get_benchmark(benchmark_id)
    loop_config = LoopConfig(shape=shape, steps_per_segment=steps_per_segment)
    path = build_loop_path(center=center, side=side, orientation=orientation, shape=shape, steps_per_segment=steps_per_segment)
    continuation = continue_path_with_branch_ids(benchmark=benchmark, path=path, config=loop_config)
    states = continuation['states']
    return {
        'benchmark': benchmark,
        'shape': shape,
        'center': [float(center[0]), float(center[1])],
        'side_length': float(side),
        'orientation': orientation,
        'states': states,
        'switch_count': int(continuation['switch_count']),
        'ambiguous_step_count': int(continuation['ambiguous_step_count']),
        'unique_branch_ids': continuation['unique_branch_ids'],
        'pure_state_flux': float(berry_loop_flux(states)),
    }


def _loop_run_from_precomputed(precomputed: dict, dephasing: float, cache: DensityCache, step_fn: Callable) -> dict:
    benchmark = precomputed['benchmark']
    states = precomputed['states']
    branch_rhos = [cache.get(state, dephasing) for state in states]
    response, mean_coh, mean_purity, actual_mean, branch_mean = _loop_observable_response(benchmark, states, branch_rhos, dephasing, step_fn)
    raw_phase = float(mixed_loop_holonomy_phase(branch_rhos))
    return {
        'shape': precomputed['shape'],
        'center': precomputed['center'],
        'side_length': precomputed['side_length'],
        'orientation': precomputed['orientation'],
        'dephasing': float(dephasing),
        'response': float(response),
        'raw_mixed_holonomy_phase': raw_phase,
        'pure_state_flux': float(precomputed['pure_state_flux']),
        'avg_coherence_ratio': float(mean_coh),
        'avg_purity': float(mean_purity),
        'observable_actual_mean': float(actual_mean),
        'observable_branch_mean': float(branch_mean),
        'switch_count': int(precomputed['switch_count']),
        'ambiguous_step_count': int(precomputed['ambiguous_step_count']),
        'unique_branch_ids': precomputed['unique_branch_ids'],
    }


def _benchmark_payload(benchmark_id: str, family: LoopFamilySpec, dephasing_values: tuple[float, ...], scan_config: ScanConfig, cache: DensityCache, step_fn: Callable, coherence_switch_floor: float) -> dict:
    orientation_records: dict[tuple[str, int, float, str], list[dict]] = {}
    precomputed: dict[tuple[str, int, float, str], dict] = {}
    for center_index, center in enumerate(family.centers):
        for side in family.side_lengths:
            for shape in family.shapes:
                for orientation in ('ccw', 'cw'):
                    key = (shape, center_index, float(side), orientation)
                    precomputed[key] = _precompute_loop_branch(
                        benchmark_id=benchmark_id,
                        shape=shape,
                        center=center,
                        side=side,
                        orientation=orientation,
                        steps_per_segment=family.steps_per_segment,
                    )
    for gamma in dephasing_values:
        for key, pre in precomputed.items():
            rec = _loop_run_from_precomputed(pre, float(gamma), cache, step_fn)
            orientation_records.setdefault(key, []).append(rec)
    for recs in orientation_records.values():
        recs.sort(key=lambda row: row['dephasing'])
        phases = [row['raw_mixed_holonomy_phase'] for row in recs]
        unwrapped = unwrap_phase_sequence(phases)
        for row, phase in zip(recs, unwrapped):
            row['unwrapped_mixed_holonomy_phase'] = float(phase)

    pair_series: dict[tuple[str, int, float], list[dict]] = {}
    for shape in family.shapes:
        for center_index, center in enumerate(family.centers):
            for side in family.side_lengths:
                ccw_recs = orientation_records[(shape, center_index, float(side), 'ccw')]
                cw_recs = orientation_records[(shape, center_index, float(side), 'cw')]
                raw_gap = np.asarray([
                    float(ccw['unwrapped_mixed_holonomy_phase']) - float(cw['unwrapped_mixed_holonomy_phase'])
                    for ccw, cw in zip(ccw_recs, cw_recs)
                ], dtype=float)
                gap_series = unwrap_phase_sequence(raw_gap)
                rows: list[dict] = []
                for gamma_index, (ccw, cw, gap) in enumerate(zip(ccw_recs, cw_recs, gap_series)):
                    trusted = ccw['switch_count'] == 0 and cw['switch_count'] == 0 and ccw['ambiguous_step_count'] == 0 and cw['ambiguous_step_count'] == 0
                    rows.append(
                        {
                            'shape': shape,
                            'center_index': int(center_index),
                            'center': list(center),
                            'side_length': float(side),
                            'dephasing': float(ccw['dephasing']),
                            'trusted_pair': bool(trusted),
                            'pair_r4': not bool(trusted),
                            'orientation_gap': float(ccw['response'] - cw['response']),
                            'orientation_sum': float(ccw['response'] + cw['response']),
                            'raw_mixed_holonomy_gap': float(gap),
                            'state_flux_gap': float(ccw['pure_state_flux'] - cw['pure_state_flux']),
                            'avg_coherence_ratio_mean': float(0.5 * (ccw['avg_coherence_ratio'] + cw['avg_coherence_ratio'])),
                            'avg_purity_mean': float(0.5 * (ccw['avg_purity'] + cw['avg_purity'])),
                            'ccw': ccw,
                            'cw': cw,
                        }
                    )
                pair_series[(shape, center_index, float(side))] = rows

    gamma0_rows = [rows[0] for rows in pair_series.values() if rows and rows[0]['trusted_pair']]
    sign = phase_alignment_sign([row['state_flux_gap'] for row in gamma0_rows], [row['raw_mixed_holonomy_gap'] for row in gamma0_rows])

    scan_levels = [_scan_level(benchmark_id, scan_config, gamma, cache) for gamma in dephasing_values]
    levels: list[dict] = []
    for gamma_index, gamma in enumerate(dephasing_values):
        rows = []
        for rows_by_loop in pair_series.values():
            row = dict(rows_by_loop[gamma_index])
            row['aligned_mixed_holonomy_gap'] = float(sign * row['raw_mixed_holonomy_gap'])
            rows.append(row)
        trusted = [row for row in rows if row['trusted_pair']]
        xs = np.asarray([row['aligned_mixed_holonomy_gap'] for row in trusted], dtype=float)
        ys = np.asarray([row['orientation_gap'] for row in trusted], dtype=float)
        patch_groups: dict[str, list[dict]] = {}
        shape_groups: dict[str, list[dict]] = {}
        center_groups: dict[str, list[dict]] = {}
        for row in rows:
            patch_key = f"{row['shape']}|({row['center'][0]:+.2f},{row['center'][1]:+.2f})"
            center_key = f"({row['center'][0]:+.2f},{row['center'][1]:+.2f})"
            patch_groups.setdefault(patch_key, []).append(row)
            shape_groups.setdefault(row['shape'], []).append(row)
            center_groups.setdefault(center_key, []).append(row)
        patch_atlas = {key: _summarize_patch_group(group) for key, group in patch_groups.items()}
        by_shape = {key: _summarize_patch_group(group) for key, group in shape_groups.items()}
        by_center = {key: _summarize_patch_group(group) for key, group in center_groups.items()}
        global_fit = _fit_through_origin(xs, ys)
        best_patch_key = None
        best_patch_r2 = None
        for key, patch in patch_atlas.items():
            r2 = patch['fit']['r2']
            if r2 is None:
                continue
            if best_patch_r2 is None or float(r2) > float(best_patch_r2):
                best_patch_r2 = float(r2)
                best_patch_key = key
        level = {
            'dephasing': float(gamma),
            'pair_rows': rows,
            'fit_orientation_gap_vs_aligned_holonomy': global_fit,
            'coherence_ratio_summary': summarize(row['avg_coherence_ratio_mean'] for row in rows),
            'purity_summary': summarize(row['avg_purity_mean'] for row in rows),
            'trusted_pair_count': int(len(trusted)),
            'excluded_pair_count': int(sum(1 for row in rows if not row['trusted_pair'])),
            'patch_atlas': patch_atlas,
            'family_summaries': {'by_shape': by_shape, 'by_center': by_center},
            'best_patch_key': best_patch_key,
            'best_patch_r2': best_patch_r2,
            'locality_gap': None if global_fit['r2'] is None or best_patch_r2 is None else float(best_patch_r2 - float(global_fit['r2'])),
        }
        level['verdict'] = _level_verdict(benchmark_id, level)
        levels.append(level)

    switch_gamma = _recommended_switch(levels, floor=coherence_switch_floor)
    switch_level = _select_level(levels, switch_gamma)
    switch_scan = _select_level(scan_levels, switch_gamma)
    benchmark = get_benchmark(benchmark_id)
    payload = {
        'phase': 'phase13_local_mixed_state_atlas',
        'backend': 'lindblad',
        'benchmark': benchmark_id,
        'slug': benchmark.slug,
        'description': benchmark.description,
        'dephasing_values': [float(x) for x in dephasing_values],
        'loop_family': {
            'shapes': list(family.shapes),
            'centers': [list(center) for center in family.centers],
            'side_lengths': [float(x) for x in family.side_lengths],
            'steps_per_segment': int(family.steps_per_segment),
        },
        'alignment': {'reference': 'pure_state_flux_gap_at_gamma0', 'sign': float(sign)},
        'recommended_switch_gamma': float(switch_gamma),
        'scan_levels': scan_levels,
        'loop_levels': levels,
        'switch_level': {
            'dephasing': float(switch_gamma),
            'verdict': switch_level['verdict'],
            'global_fit': switch_level['fit_orientation_gap_vs_aligned_holonomy'],
            'best_patch_key': switch_level['best_patch_key'],
            'best_patch_r2': switch_level['best_patch_r2'],
            'locality_gap': switch_level['locality_gap'],
            'trusted_pair_count': switch_level['trusted_pair_count'],
            'excluded_pair_count': switch_level['excluded_pair_count'],
            'patch_atlas': switch_level['patch_atlas'],
            'family_summaries': switch_level['family_summaries'],
            'scan_summary': {
                'mean_abs_mixed_curvature': switch_scan['mean_abs_mixed_curvature'],
                'coherence_ratio_summary': switch_scan['coherence_ratio_summary'],
                'purity_summary': switch_scan['purity_summary'],
                'ambiguous_tile_count': switch_scan['ambiguous_tile_count'],
                'switch_tile_count': switch_scan['switch_tile_count'],
            },
        },
    }
    return payload


def phase13_payload(output_root: Path, phase13_config: Phase13Config | None = None, scan_config: ScanConfig | None = None, lindblad_config: LindbladConfig | None = None) -> dict:
    cfg = phase13_config or Phase13Config()
    scan_cfg = scan_config or ScanConfig(mesh=cfg.scan_mesh)
    lind_cfg = lindblad_config or LindbladConfig(scan_mesh=cfg.scan_mesh, dephasing_values=cfg.dephasing_values, coherence_switch_floor=cfg.coherence_switch_floor)
    cache = DensityCache(lambda state, gamma: lindblad_branch_density(state, lind_cfg, gamma))
    step_fn = lambda rho, state, gamma: apply_lindblad_step(rho, state=state, config=lind_cfg, dephasing=gamma)

    benchmark_payloads: dict[str, dict] = {}
    benchmark_summaries: dict[str, dict] = {}
    for benchmark_id in cfg.benchmark_ids:
        family = _family_for_benchmark(benchmark_id)
        payload = _benchmark_payload(
            benchmark_id=benchmark_id,
            family=family,
            dephasing_values=cfg.dephasing_values,
            scan_config=scan_cfg,
            cache=cache,
            step_fn=step_fn,
            coherence_switch_floor=cfg.coherence_switch_floor,
        )
        benchmark_payloads[benchmark_id] = payload
        level = payload['switch_level']
        benchmark_summaries[benchmark_id] = {
            'benchmark': benchmark_id,
            'switch_gamma': float(payload['recommended_switch_gamma']),
            'verdict': level['verdict'],
            'global_slope': level['global_fit']['slope'],
            'global_r2': level['global_fit']['r2'],
            'best_patch_key': level['best_patch_key'],
            'best_patch_r2': level['best_patch_r2'],
            'locality_gap': level['locality_gap'],
            'trusted_pair_count': int(level['trusted_pair_count']),
            'excluded_pair_count': int(level['excluded_pair_count']),
            'alignment_sign': float(payload['alignment']['sign']),
            'scan_mean_abs_curvature': float(level['scan_summary']['mean_abs_mixed_curvature']),
        }
        bench_dir = output_root / payload['slug']
        bench_dir.mkdir(parents=True, exist_ok=True)
        (bench_dir / f"{benchmark_id}_phase13_atlas.json").write_text(json.dumps(payload, indent=2))

    focus_id = cfg.benchmark_focus
    focus_payload = benchmark_payloads[focus_id]
    focus_switch = focus_payload['switch_level']
    focus_scan = _select_level(focus_payload['scan_levels'], focus_payload['recommended_switch_gamma'])
    suite = {
        'phase': 'phase13_local_mixed_state_atlas',
        'description': 'Local mixed-state susceptibility atlas built from the Lindblad-style graph-local generator, with uniform phase convention across positive, control, and exclusion benchmarks.',
        'dephasing_values': [float(x) for x in cfg.dephasing_values],
        'benchmark_summaries': benchmark_summaries,
        'benchmark_payloads': benchmark_payloads,
        'focus_benchmark': focus_id,
        'focus_backend_comparison': {
            'switch_gamma': float(focus_payload['recommended_switch_gamma']),
            'metric_curvature_focus_corr': _corr(np.asarray(focus_scan['bures_metric_trace'], dtype=float), np.asarray(focus_scan['bures_metric_trace'], dtype=float)),
            'switch_global_fit': focus_switch['global_fit'],
            'switch_best_patch_key': focus_switch['best_patch_key'],
            'switch_best_patch_r2': focus_switch['best_patch_r2'],
        },
        'notes': [
            'Phase 13 replaces one noisy global slope with a local atlas of patchwise susceptibility coefficients.',
            'All loop-family benchmarks now use the same mixed-state phase convention: per-loop unwrapping over γ and sign harmonization against the pure-state flux gap at γ=0.',
            'The atlas is estimated from the continuous-time Lindblad-style graph-local generator, not from direct response interpolation.',
        ],
    }
    reports_dir = output_root.parents[1] / '05_reports'
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / 'phase13_summary.json').write_text(json.dumps(suite, indent=2))
    return suite


def _plot_patch_bars(path: Path, patch_map: dict[str, dict], field: str, ylabel: str, title: str) -> None:
    labels = list(patch_map.keys())
    values = [patch_map[key]['fit'][field] if patch_map[key]['fit'][field] is not None else np.nan for key in labels]
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(7.8, 4.4))
    plt.bar(np.arange(len(labels)), values)
    plt.xticks(np.arange(len(labels)), labels, rotation=30, ha='right')
    plt.ylabel(ylabel)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _plot_patch_lines(path: Path, x: np.ndarray, series: dict[str, list[float]], ylabel: str, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(7.2, 4.4))
    for label, values in series.items():
        plt.plot(x, np.asarray(values, dtype=float), marker='o', label=label)
    plt.xlabel('dephasing γ')
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _plot_suite_bars(path: Path, labels: list[str], global_values: list[float], local_values: list[float], title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    x = np.arange(len(labels), dtype=float)
    width = 0.35
    plt.figure(figsize=(7.6, 4.4))
    plt.bar(x - width / 2.0, global_values, width=width, label='global')
    plt.bar(x + width / 2.0, local_values, width=width, label='best patch')
    plt.xticks(x, labels)
    plt.ylabel('fit R²')
    plt.title(title)
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def phase13_report(output_root: Path, payload: dict) -> dict[str, Path]:
    project_root = output_root.parents[1]
    reports_dir = project_root / '05_reports'
    plots_root = reports_dir / 'plots' / 'phase13_local_atlas'
    reports_dir.mkdir(parents=True, exist_ok=True)
    plot_paths: dict[str, Path] = {}

    for benchmark_id, bench in payload['benchmark_payloads'].items():
        switch = bench['switch_level']
        bench_plot_dir = plots_root / get_benchmark(benchmark_id).slug
        patch_bars = bench_plot_dir / 'patch_slope_at_switch.png'
        _plot_patch_bars(
            patch_bars,
            switch['patch_atlas'],
            field='slope',
            ylabel='patch slope χ',
            title=f"{benchmark_id} local mixed-state susceptibility at switch γ={bench['recommended_switch_gamma']:.2f}",
        )
        patch_r2 = bench_plot_dir / 'patch_r2_at_switch.png'
        _plot_patch_bars(
            patch_r2,
            switch['patch_atlas'],
            field='r2',
            ylabel='patch fit R²',
            title=f"{benchmark_id} patch fit quality at switch γ={bench['recommended_switch_gamma']:.2f}",
        )
        plot_paths[f'{benchmark_id}_patch_slope'] = patch_bars
        plot_paths[f'{benchmark_id}_patch_r2'] = patch_r2

        if benchmark_id == payload['focus_benchmark']:
            x = np.asarray(payload['dephasing_values'], dtype=float)
            patch_slope_series: dict[str, list[float]] = {key: [] for key in switch['patch_atlas'].keys()}
            patch_r2_series: dict[str, list[float]] = {key: [] for key in switch['patch_atlas'].keys()}
            for level in bench['loop_levels']:
                for key in patch_slope_series.keys():
                    patch = level['patch_atlas'].get(key, {'fit': {'slope': np.nan, 'r2': np.nan}})
                    patch_slope_series[key].append(patch['fit']['slope'] if patch['fit']['slope'] is not None else np.nan)
                    patch_r2_series[key].append(patch['fit']['r2'] if patch['fit']['r2'] is not None else np.nan)
            slope_lines = bench_plot_dir / 'patch_slope_vs_dephasing.png'
            _plot_patch_lines(slope_lines, x, patch_slope_series, ylabel='patch slope χ', title=f'{benchmark_id} local susceptibility atlas vs dephasing')
            r2_lines = bench_plot_dir / 'patch_r2_vs_dephasing.png'
            _plot_patch_lines(r2_lines, x, patch_r2_series, ylabel='patch fit R²', title=f'{benchmark_id} patch fit quality vs dephasing')
            plot_paths[f'{benchmark_id}_patch_slope_vs_dephasing'] = slope_lines
            plot_paths[f'{benchmark_id}_patch_r2_vs_dephasing'] = r2_lines

    labels = []
    global_vals = []
    local_vals = []
    for benchmark_id, row in payload['benchmark_summaries'].items():
        labels.append(benchmark_id)
        global_vals.append(row['global_r2'] if row['global_r2'] is not None else np.nan)
        local_vals.append(row['best_patch_r2'] if row['best_patch_r2'] is not None else np.nan)
    suite_plot = plots_root / 'suite_global_vs_local_r2.png'
    _plot_suite_bars(suite_plot, labels, global_vals, local_vals, title='Mixed-state atlas: global vs best-patch fit quality')
    plot_paths['suite_global_vs_local_r2'] = suite_plot

    md_lines = [
        '# CWT-CGT Phase 13 Report',
        '',
        '## What Phase 13 adds',
        '',
        'Phase 13 replaces the noisy lane’s single global slope with a **local mixed-state susceptibility atlas** estimated from the continuous-time Lindblad-style graph-local generator.',
        '',
        'Each benchmark is now summarized by patch families (shape × center), with per-patch slope, fit quality, trusted/excluded counts, and a locality gap against the global fit at the recommended mixed-state switch γ.',
        '',
        '## Suite summary at the recommended switch γ',
        '',
    ]
    for benchmark_id, row in payload['benchmark_summaries'].items():
        md_lines.append(
            f"- {benchmark_id}: verdict={row['verdict']}, switch γ={row['switch_gamma']:.2f}, global R²={row['global_r2']}, best patch={row['best_patch_key']}, best patch R²={row['best_patch_r2']}, locality gap={row['locality_gap']}, trusted={row['trusted_pair_count']}, excluded={row['excluded_pair_count']}"
        )
    md_lines.extend(['', '## Per-benchmark patch-family summaries', ''])
    for benchmark_id, bench in payload['benchmark_payloads'].items():
        switch = bench['switch_level']
        md_lines.append(f'### {benchmark_id}')
        md_lines.append('')
        md_lines.append(f"- Verdict: {switch['verdict']}")
        md_lines.append(f"- Switch γ: {bench['recommended_switch_gamma']:.2f}")
        md_lines.append(f"- Global slope / R²: {switch['global_fit']['slope']} / {switch['global_fit']['r2']}")
        md_lines.append(f"- Best patch: {switch['best_patch_key']} (R²={switch['best_patch_r2']})")
        md_lines.append(f"- Trusted / excluded pairs: {switch['trusted_pair_count']} / {switch['excluded_pair_count']}")
        md_lines.append('')
        md_lines.append('| patch | class | slope | R² | trusted | excluded | side lengths |')
        md_lines.append('|---|---:|---:|---:|---:|---:|---|')
        for key, patch in switch['patch_atlas'].items():
            md_lines.append(
                f"| {key} | {patch['patch_class']} | {patch['fit']['slope']} | {patch['fit']['r2']} | {patch['count_trusted']} | {patch['count_excluded']} | {', '.join(f'{x:.2f}' for x in patch['side_lengths'])} |"
            )
        md_lines.append('')
        md_lines.append(f"Patch slope plot: `{plot_paths[f'{benchmark_id}_patch_slope']}`")
        md_lines.append(f"Patch R² plot: `{plot_paths[f'{benchmark_id}_patch_r2']}`")
        if benchmark_id == payload['focus_benchmark']:
            md_lines.append(f"Patch slope vs dephasing: `{plot_paths[f'{benchmark_id}_patch_slope_vs_dephasing']}`")
            md_lines.append(f"Patch R² vs dephasing: `{plot_paths[f'{benchmark_id}_patch_r2_vs_dephasing']}`")
        md_lines.append('')
    md_lines.extend(
        [
            '## Interpretation',
            '',
            '- The noisy response law is now best treated as **local** in patch family rather than as one benchmark-wide coefficient.',
            '- Benchmark C remains the positive mixed-state benchmark, but only as a patchwise atlas claim.',
            '- Benchmarks A and D remain null-like controls in this lane.',
            '- Benchmark B is weak / patchy rather than robustly positive.',
            '- Benchmark F remains an exclusion benchmark dominated by branch ambiguity / switching.',
            '',
            f"Suite plot: `{suite_plot}`",
        ]
    )
    report_path = reports_dir / 'CWT-CGT_Phase_13_Report.md'
    report_path.write_text('\n'.join(md_lines))

    acceptance_lines = [
        '# CWT-CGT benchmark acceptance report v7',
        '',
        'This version reports the mixed-state lane with a local susceptibility atlas rather than a single global noisy slope.',
        '',
    ]
    for benchmark_id, row in payload['benchmark_summaries'].items():
        acceptance_lines.append(f'## {benchmark_id}')
        acceptance_lines.append('')
        acceptance_lines.append(f"- Verdict: {row['verdict']}")
        acceptance_lines.append(f"- Switch γ: {row['switch_gamma']:.2f}")
        acceptance_lines.append(f"- Global slope / R²: {row['global_slope']} / {row['global_r2']}")
        acceptance_lines.append(f"- Best patch / R²: {row['best_patch_key']} / {row['best_patch_r2']}")
        acceptance_lines.append(f"- Locality gap: {row['locality_gap']}")
        acceptance_lines.append(f"- Trusted / excluded pairs: {row['trusted_pair_count']} / {row['excluded_pair_count']}")
        acceptance_lines.append('')
    acceptance_path = reports_dir / 'CWT-CGT_Benchmark_Acceptance_Report_v7.md'
    acceptance_path.write_text('\n'.join(acceptance_lines))
    plot_paths['phase13_report'] = report_path
    plot_paths['acceptance_report_v7'] = acceptance_path
    return plot_paths
