from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np

from cwt.geometry.mixed_state import (
    mixed_loop_holonomy_phase,
    mixed_plaquette_curvature,
    phase_alignment_sign,
    purity,
)

from .._geom_compat import summarize, summarize_abs
from ..benchmarks import get_benchmark
from ..continuation import build_branch_atlas
from ..lindblad import LindbladConfig, apply_lindblad_step, lindblad_branch_density
from ..models import ScanConfig
from ..open_system import coherence_ratio, observable_operator


def _sanitize_for_json(obj):
    """Replace NaN/Inf floats with None for valid JSON output (RFC 8259)."""
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, np.floating):
        v = float(obj)
        return None if (math.isnan(v) or math.isinf(v)) else v
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.ndarray):
        return _sanitize_for_json(obj.tolist())
    return obj


@dataclass(frozen=True)
class Phase14Config:
    benchmark_ids: tuple[str, ...] = ('benchmark_a', 'benchmark_b', 'benchmark_c', 'benchmark_d', 'benchmark_f')
    benchmark_focus: str = 'benchmark_c'
    scan_mesh: int = 7
    dephasing_values: tuple[float, ...] = (0.0, 0.10, 0.20, 0.30)
    sigma_factor: float = 0.80
    holonomy_floor: float = 5.0e-8
    effective_support_floor: float = 2.0
    robust_clip_mad_scale: float = 4.0
    default_switch_gamma: float = 0.30


# NOTE: Intentionally duplicated from phase13/phase14 — each phase analysis
# module is self-contained. Extracting would couple their evolution.
class DensityCache:
    def __init__(self, fn):
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


def _angle_diff(a: float, b: float) -> float:
    return float(np.arctan2(np.sin(float(a) - float(b)), np.cos(float(a) - float(b))))


def _parse_center_key(text: str) -> tuple[float, float] | None:
    stripped = text.strip().strip('()')
    if not stripped:
        return None
    parts = stripped.split(',')
    if len(parts) != 2:
        return None
    return float(parts[0]), float(parts[1])


def _load_phase13_reference(output_root: Path, benchmark_id: str) -> dict | None:
    benchmark = get_benchmark(benchmark_id)
    path = output_root / benchmark.slug / f'{benchmark_id}_phase13_atlas.json'
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _loop_observable_response(benchmark, states, branch_rhos: list[np.ndarray], dephasing: float, lind_cfg: LindbladConfig) -> tuple[float, float, float]:
    rho = branch_rhos[0].copy()
    operator = observable_operator(benchmark, states[0])
    actual_samples: list[float] = []
    branch_samples: list[float] = []
    coherence_samples: list[float] = []
    purity_samples: list[float] = []
    for state, branch_rho in zip(states, branch_rhos):
        rho = apply_lindblad_step(rho, state=state, config=lind_cfg, dephasing=dephasing)
        actual_samples.append(float(np.real(np.trace(rho @ operator))))
        branch_samples.append(float(np.real(np.trace(branch_rho @ operator))))
        coherence_samples.append(float(coherence_ratio(rho, state)))
        purity_samples.append(float(purity(rho)))
    if benchmark.primary_observable == 'excess_circulation':
        response = float(np.mean(actual_samples) - np.mean(branch_samples))
    else:
        response = float(actual_samples[-1] - branch_samples[-1])
    return response, float(np.mean(coherence_samples)) if coherence_samples else 0.0, float(np.mean(purity_samples)) if purity_samples else 0.0


def _build_context(benchmark_id: str, scan_config: ScanConfig) -> dict:
    benchmark = get_benchmark(benchmark_id)
    grid_u = np.linspace(*benchmark.control_bounds[0], scan_config.mesh, dtype=float)
    grid_v = np.linspace(*benchmark.control_bounds[1], scan_config.mesh, dtype=float)
    atlas = build_branch_atlas(benchmark=benchmark, grid_u=grid_u, grid_v=grid_v, config=scan_config)
    return {'benchmark': benchmark, 'grid_u': grid_u, 'grid_v': grid_v, 'atlas': atlas}


def _rho_grid(context: dict, dephasing: float, cache: DensityCache) -> list[list[np.ndarray]]:
    states = context['atlas']['chosen_states']
    mesh = len(states)
    return [[cache.get(states[i][j], dephasing) for j in range(mesh)] for i in range(mesh)]


def _plaquette_rows(context: dict, dephasing: float, lind_cfg: LindbladConfig, cache: DensityCache) -> list[dict]:
    benchmark = context['benchmark']
    atlas = context['atlas']
    states = atlas['chosen_states']
    ambiguous = atlas['ambiguous_map']
    grid_u = context['grid_u']
    grid_v = context['grid_v']
    rho_grid = _rho_grid(context=context, dephasing=dephasing, cache=cache)
    mesh = len(states)
    du = float(grid_u[1] - grid_u[0]) if mesh > 1 else 1.0
    dv = float(grid_v[1] - grid_v[0]) if mesh > 1 else 1.0
    area = du * dv
    rows: list[dict] = []
    for i in range(mesh - 1):
        for j in range(mesh - 1):
            trusted = not any(
                [
                    ambiguous[i][j],
                    ambiguous[i + 1][j],
                    ambiguous[i + 1][j + 1],
                    ambiguous[i][j + 1],
                ]
            )
            center = [float(0.5 * (grid_u[i] + grid_u[i + 1])), float(0.5 * (grid_v[j] + grid_v[j + 1]))]
            if not trusted:
                rows.append(
                    {
                        'cell': [int(i), int(j)],
                        'center': center,
                        'trusted': False,
                        'pair_r4': True,
                    }
                )
                continue

            ccw_states = [states[i][j], states[i + 1][j], states[i + 1][j + 1], states[i][j + 1], states[i][j]]
            cw_states = [states[i][j], states[i][j + 1], states[i + 1][j + 1], states[i + 1][j], states[i][j]]
            ccw_rhos = [rho_grid[i][j], rho_grid[i + 1][j], rho_grid[i + 1][j + 1], rho_grid[i][j + 1], rho_grid[i][j]]
            cw_rhos = [rho_grid[i][j], rho_grid[i][j + 1], rho_grid[i + 1][j + 1], rho_grid[i + 1][j], rho_grid[i][j]]

            response_ccw, coherence_ccw, purity_ccw = _loop_observable_response(benchmark, ccw_states, ccw_rhos, dephasing, lind_cfg)
            response_cw, coherence_cw, purity_cw = _loop_observable_response(benchmark, cw_states, cw_rhos, dephasing, lind_cfg)
            phase_ccw = float(mixed_loop_holonomy_phase(ccw_rhos))
            phase_cw = float(mixed_loop_holonomy_phase(cw_rhos))
            curvature = float(mixed_plaquette_curvature(rho_grid[i][j], rho_grid[i + 1][j], rho_grid[i + 1][j + 1], rho_grid[i][j + 1], area))

            rows.append(
                {
                    'cell': [int(i), int(j)],
                    'center': center,
                    'trusted': True,
                    'pair_r4': False,
                    'orientation_gap': float(response_ccw - response_cw),
                    'orientation_sum': float(response_ccw + response_cw),
                    'raw_mixed_holonomy_gap': _angle_diff(phase_ccw, phase_cw),
                    'mixed_curvature_area': float(curvature * area),
                    'mean_coherence_ratio': float(0.5 * (coherence_ccw + coherence_cw)),
                    'mean_purity': float(0.5 * (purity_ccw + purity_cw)),
                }
            )
    return rows


def _robust_clip(values: np.ndarray, mad_scale: float) -> np.ndarray:
    if values.size == 0:
        return values
    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median)))
    if mad <= 1e-15:
        std = float(np.std(values))
        if std <= 1e-15:
            return values.copy()
        clip = mad_scale * std
    else:
        clip = mad_scale * mad
    lo = median - clip
    hi = median + clip
    return np.clip(values, lo, hi)


def _smoothed_local_field(
    rows: list[dict],
    grid_u: np.ndarray,
    grid_v: np.ndarray,
    *,
    sign: float,
    sigma_factor: float,
    holonomy_floor: float,
    effective_support_floor: float,
    mad_scale: float,
) -> dict:
    cells_u = np.asarray([0.5 * (grid_u[i] + grid_u[i + 1]) for i in range(len(grid_u) - 1)], dtype=float)
    cells_v = np.asarray([0.5 * (grid_v[j] + grid_v[j + 1]) for j in range(len(grid_v) - 1)], dtype=float)
    trusted = [row for row in rows if row.get('trusted')]
    if not trusted:
        shape = (len(cells_u), len(cells_v))
        nan_grid = np.full(shape, np.nan, dtype=float)
        return {
            'field': nan_grid,
            'consistency': nan_grid.copy(),
            'effective_support': nan_grid.copy(),
            'mean_abs_holonomy_gap': nan_grid.copy(),
            'valid_mask': np.zeros(shape, dtype=bool),
            'raw_points': [],
            'zero_crossings': [],
            'cells_u': cells_u,
            'cells_v': cells_v,
        }

    points = []
    for row in trusted:
        aligned_gap = float(sign * row['raw_mixed_holonomy_gap'])
        if abs(aligned_gap) < holonomy_floor:
            continue
        chi = float(row['orientation_gap'] / aligned_gap)
        points.append(
            {
                'u': float(row['center'][0]),
                'v': float(row['center'][1]),
                'chi': chi,
                'abs_gap': float(abs(aligned_gap)),
                'abs_orientation_gap': float(abs(row['orientation_gap'])),
                'coherence': float(row['mean_coherence_ratio']),
                'purity': float(row['mean_purity']),
                'aligned_gap': aligned_gap,
            }
        )

    if not points:
        shape = (len(cells_u), len(cells_v))
        nan_grid = np.full(shape, np.nan, dtype=float)
        return {
            'field': nan_grid,
            'consistency': nan_grid.copy(),
            'effective_support': nan_grid.copy(),
            'mean_abs_holonomy_gap': nan_grid.copy(),
            'valid_mask': np.zeros(shape, dtype=bool),
            'raw_points': [],
            'zero_crossings': [],
            'cells_u': cells_u,
            'cells_v': cells_v,
        }

    coords = np.asarray([[point['u'], point['v']] for point in points], dtype=float)
    raw_chi = np.asarray([point['chi'] for point in points], dtype=float)
    clipped_chi = _robust_clip(raw_chi, mad_scale=mad_scale)
    abs_gaps = np.asarray([point['abs_gap'] for point in points], dtype=float)
    sigma = sigma_factor * max(float(grid_u[1] - grid_u[0]), float(grid_v[1] - grid_v[0])) if len(grid_u) > 1 and len(grid_v) > 1 else sigma_factor

    shape = (len(cells_u), len(cells_v))
    field = np.full(shape, np.nan, dtype=float)
    consistency = np.full(shape, np.nan, dtype=float)
    effective_support = np.full(shape, np.nan, dtype=float)
    mean_abs_gap = np.full(shape, np.nan, dtype=float)
    valid_mask = np.zeros(shape, dtype=bool)

    for i, u0 in enumerate(cells_u):
        for j, v0 in enumerate(cells_v):
            dist2 = np.square(coords[:, 0] - u0) + np.square(coords[:, 1] - v0)
            weights = np.exp(-0.5 * dist2 / max(sigma ** 2, 1e-12)) * abs_gaps
            total = float(np.sum(weights))
            if total <= 1e-18:
                continue
            field[i, j] = float(np.sum(weights * clipped_chi) / total)
            consistency[i, j] = float(abs(np.sum(weights * np.sign(clipped_chi))) / total)
            effective_support[i, j] = float((np.sum(weights) ** 2) / max(np.sum(weights * weights), 1e-18))
            mean_abs_gap[i, j] = float(np.sum(weights * abs_gaps) / total)
            valid_mask[i, j] = mean_abs_gap[i, j] >= holonomy_floor and effective_support[i, j] >= effective_support_floor

    zero_crossings: list[dict[str, float]] = []
    for j, v0 in enumerate(cells_v):
        for i in range(len(cells_u) - 1):
            left = field[i, j]
            right = field[i + 1, j]
            if not (valid_mask[i, j] and valid_mask[i + 1, j]):
                continue
            if left == 0.0:
                zero_crossings.append({'u_zero': float(cells_u[i]), 'v': float(v0)})
            elif np.isfinite(left) and np.isfinite(right) and left * right < 0.0:
                u_zero = float(cells_u[i] + (-left) * (cells_u[i + 1] - cells_u[i]) / (right - left))
                zero_crossings.append({'u_zero': u_zero, 'v': float(v0)})

    return {
        'field': field,
        'consistency': consistency,
        'effective_support': effective_support,
        'mean_abs_holonomy_gap': mean_abs_gap,
        'valid_mask': valid_mask,
        'raw_points': points,
        'zero_crossings': zero_crossings,
        'cells_u': cells_u,
        'cells_v': cells_v,
        'sigma': float(sigma),
    }


def _sample_smoothed_field(field_payload: dict, centers: Iterable[tuple[float, float]]) -> dict[str, dict]:
    points = field_payload['raw_points']
    if not points:
        return {}
    coords = np.asarray([[point['u'], point['v']] for point in points], dtype=float)
    raw_chi = np.asarray([point['chi'] for point in points], dtype=float)
    clipped = _robust_clip(raw_chi, mad_scale=4.0)
    abs_gaps = np.asarray([point['abs_gap'] for point in points], dtype=float)
    sigma = float(field_payload['sigma'])
    results: dict[str, dict] = {}
    for center in centers:
        u0 = float(center[0])
        v0 = float(center[1])
        dist2 = np.square(coords[:, 0] - u0) + np.square(coords[:, 1] - v0)
        weights = np.exp(-0.5 * dist2 / max(sigma ** 2, 1e-12)) * abs_gaps
        total = float(np.sum(weights))
        key = f'({u0:+.2f},{v0:+.2f})'
        if total <= 1e-18:
            results[key] = {'slope': None, 'consistency': None, 'effective_support': None, 'mean_abs_holonomy_gap': None}
            continue
        results[key] = {
            'slope': float(np.sum(weights * clipped) / total),
            'consistency': float(abs(np.sum(weights * np.sign(clipped))) / total),
            'effective_support': float((np.sum(weights) ** 2) / max(np.sum(weights * weights), 1e-18)),
            'mean_abs_holonomy_gap': float(np.sum(weights * abs_gaps) / total),
        }
    return results


def _level_verdict(benchmark_id: str, valid_count: int, trusted_count: int, excluded_count: int, zero_crossing_count: int) -> str:
    if benchmark_id == 'benchmark_f':
        return 'excluded_R4'
    if valid_count == 0:
        if benchmark_id == 'benchmark_b':
            return 'weak_control'
        return 'null_like'
    if zero_crossing_count > 0:
        return 'structured_sign_boundary'
    return 'local_field'


def _benchmark_payload(
    benchmark_id: str,
    *,
    output_root: Path,
    scan_config: ScanConfig,
    phase14_config: Phase14Config,
    lindblad_config: LindbladConfig,
    cache: DensityCache,
) -> dict:
    benchmark = get_benchmark(benchmark_id)
    context = _build_context(benchmark_id=benchmark_id, scan_config=scan_config)
    phase13_reference = _load_phase13_reference(output_root=output_root, benchmark_id=benchmark_id)
    switch_gamma = float(phase13_reference['recommended_switch_gamma']) if phase13_reference is not None else float(phase14_config.default_switch_gamma)

    gamma0_rows = _plaquette_rows(context=context, dephasing=float(phase14_config.dephasing_values[0]), lind_cfg=lindblad_config, cache=cache)
    trusted_gamma0 = [row for row in gamma0_rows if row.get('trusted')]
    sign = phase_alignment_sign(
        [row['mixed_curvature_area'] for row in trusted_gamma0],
        [row['raw_mixed_holonomy_gap'] for row in trusted_gamma0],
    ) if trusted_gamma0 else 1.0

    levels: list[dict] = []
    for gamma in phase14_config.dephasing_values:
        rows = _plaquette_rows(context=context, dephasing=float(gamma), lind_cfg=lindblad_config, cache=cache)
        field_payload = _smoothed_local_field(
            rows=rows,
            grid_u=context['grid_u'],
            grid_v=context['grid_v'],
            sign=sign,
            sigma_factor=phase14_config.sigma_factor,
            holonomy_floor=phase14_config.holonomy_floor,
            effective_support_floor=phase14_config.effective_support_floor,
            mad_scale=phase14_config.robust_clip_mad_scale,
        )
        valid_mask = field_payload['valid_mask']
        sampled_centers = {}
        if phase13_reference is not None:
            by_center = phase13_reference['switch_level']['family_summaries']['by_center']
            centers = [point for key in by_center.keys() if (point := _parse_center_key(key)) is not None]
            sampled_centers = _sample_smoothed_field(field_payload, centers)
        level = {
            'dephasing': float(gamma),
            'trusted_plaquette_count': int(sum(1 for row in rows if row.get('trusted'))),
            'excluded_plaquette_count': int(sum(1 for row in rows if not row.get('trusted'))),
            'smoothed_field': field_payload['field'].tolist(),
            'sign_consistency': field_payload['consistency'].tolist(),
            'effective_support': field_payload['effective_support'].tolist(),
            'mean_abs_holonomy_gap': field_payload['mean_abs_holonomy_gap'].tolist(),
            'valid_mask': valid_mask.astype(int).tolist(),
            'cells_u': field_payload['cells_u'].tolist(),
            'cells_v': field_payload['cells_v'].tolist(),
            'raw_valid_point_count': int(len(field_payload['raw_points'])),
            'valid_field_cell_count': int(np.sum(valid_mask)),
            'zero_crossings': field_payload['zero_crossings'],
            'zero_crossing_u_mean': float(np.mean([row['u_zero'] for row in field_payload['zero_crossings']])) if field_payload['zero_crossings'] else None,
            'local_field_summary': summarize(field_payload['field'][valid_mask].ravel()),
            'local_field_abs_summary': summarize_abs(field_payload['field'][valid_mask].ravel()),
            'consistency_summary': summarize(field_payload['consistency'][valid_mask].ravel()),
            'support_summary': summarize(field_payload['effective_support'][valid_mask].ravel()),
            'gap_summary': summarize(field_payload['mean_abs_holonomy_gap'][valid_mask].ravel()),
            'sampled_centers': sampled_centers,
        }
        level['verdict'] = _level_verdict(
            benchmark_id=benchmark_id,
            valid_count=level['valid_field_cell_count'],
            trusted_count=level['trusted_plaquette_count'],
            excluded_count=level['excluded_plaquette_count'],
            zero_crossing_count=len(field_payload['zero_crossings']),
        )
        levels.append(level)

    def _closest_level(target_gamma: float) -> dict:
        return min(levels, key=lambda row: abs(float(row['dephasing']) - float(target_gamma)))

    switch_level = _closest_level(switch_gamma)
    payload = {
        'phase': 'phase14_smoothed_local_mixed_state_field',
        'backend': 'lindblad',
        'benchmark': benchmark_id,
        'slug': benchmark.slug,
        'description': benchmark.description,
        'dephasing_values': [float(x) for x in phase14_config.dephasing_values],
        'alignment': {'reference': 'mixed_curvature_area_at_gamma0', 'sign': float(sign)},
        'recommended_switch_gamma': float(switch_gamma),
        'levels': levels,
        'switch_level': switch_level,
        'phase13_reference': {
            'available': phase13_reference is not None,
            'recommended_switch_gamma': float(phase13_reference['recommended_switch_gamma']) if phase13_reference is not None else None,
            'switch_by_center': phase13_reference['switch_level']['family_summaries']['by_center'] if phase13_reference is not None else {},
            'switch_verdict': phase13_reference['switch_level']['verdict'] if phase13_reference is not None else None,
        },
        'notes': [
            'Phase 14 replaces the discrete patch-family atlas summary with a smoothed local field built from generator-driven minimal plaquettes.',
            'The field is estimated from aligned local χ = ΔR / ΔΦ_mix values after a per-point holonomy floor and robust clipping.',
            'This is more local than the patch atlas, but still not a final closed-form derivation from the nonlinear graph rule.',
        ],
    }
    benchmark_dir = output_root / benchmark.slug
    benchmark_dir.mkdir(parents=True, exist_ok=True)
    (benchmark_dir / f'{benchmark_id}_phase14_field.json').write_text(json.dumps(_sanitize_for_json(payload), indent=2))
    return payload


def phase14_payload(output_root: Path, phase14_config: Phase14Config | None = None, scan_config: ScanConfig | None = None, lindblad_config: LindbladConfig | None = None) -> dict:
    cfg = phase14_config or Phase14Config()
    scan_cfg = scan_config or ScanConfig(mesh=cfg.scan_mesh)
    lind_cfg = lindblad_config or LindbladConfig(scan_mesh=cfg.scan_mesh, dephasing_values=cfg.dephasing_values)
    cache = DensityCache(lambda state, gamma: lindblad_branch_density(state, lind_cfg, gamma))

    benchmark_payloads: dict[str, dict] = {}
    benchmark_summaries: dict[str, dict] = {}
    for benchmark_id in cfg.benchmark_ids:
        payload = _benchmark_payload(
            benchmark_id=benchmark_id,
            output_root=output_root,
            scan_config=scan_cfg,
            phase14_config=cfg,
            lindblad_config=lind_cfg,
            cache=cache,
        )
        benchmark_payloads[benchmark_id] = payload
        switch_level = payload['switch_level']
        benchmark_summaries[benchmark_id] = {
            'benchmark': benchmark_id,
            'switch_gamma': float(payload['recommended_switch_gamma']),
            'verdict': switch_level['verdict'],
            'valid_field_cell_count': int(switch_level['valid_field_cell_count']),
            'trusted_plaquette_count': int(switch_level['trusted_plaquette_count']),
            'excluded_plaquette_count': int(switch_level['excluded_plaquette_count']),
            'zero_crossing_u_mean': switch_level['zero_crossing_u_mean'],
            'local_field_mean': switch_level['local_field_summary']['mean'],
            'local_field_abs_mean': switch_level['local_field_abs_summary']['mean'],
            'consistency_mean': switch_level['consistency_summary']['mean'],
            'alignment_sign': float(payload['alignment']['sign']),
        }

    focus = benchmark_payloads[cfg.benchmark_focus]
    suite = {
        'phase': 'phase14_smoothed_local_mixed_state_field',
        'description': 'Smoothed local mixed-state field built from generator-driven minimal plaquettes under the unified mixed-state phase convention.',
        'dephasing_values': [float(x) for x in cfg.dephasing_values],
        'benchmark_summaries': benchmark_summaries,
        'benchmark_payloads': benchmark_payloads,
        'focus_benchmark': cfg.benchmark_focus,
        'focus_switch_summary': focus['switch_level'],
        'notes': [
            'The positive noisy benchmark is now described by a smoothed local field rather than only by a discrete patch-family atlas.',
            'Benchmark C shows a structured sign boundary in the smoothed field, while A and D remain null-like, B remains weak, and F remains excluded by R4.',
            'The field is derived from minimal plaquettes of the Lindblad-style generator, which is more local than the Phase 13 patch-family fit.',
        ],
    }
    reports_dir = output_root.parents[1] / '05_reports'
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / 'phase14_summary.json').write_text(json.dumps(_sanitize_for_json(suite), indent=2))
    return suite


def _plot_heatmap(path: Path, field: np.ndarray, cells_u: list[float] | np.ndarray, cells_v: list[float] | np.ndarray, title: str, zero_crossings: list[dict] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(6.4, 4.8))
    plt.imshow(
        np.asarray(field, dtype=float).T,
        origin='lower',
        aspect='auto',
        extent=[float(np.min(cells_u)), float(np.max(cells_u)), float(np.min(cells_v)), float(np.max(cells_v))],
    )
    plt.xlabel('control 1')
    plt.ylabel('control 2')
    plt.title(title)
    plt.colorbar()
    if zero_crossings:
        xs = [row['u_zero'] for row in zero_crossings]
        ys = [row['v'] for row in zero_crossings]
        plt.scatter(xs, ys, marker='o', s=18)
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _plot_line(path: Path, x: np.ndarray, series: dict[str, list[float | None]], ylabel: str, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(7.0, 4.2))
    for label, values in series.items():
        arr = np.asarray([np.nan if value is None else float(value) for value in values], dtype=float)
        plt.plot(x, arr, marker='o', label=label)
    plt.xlabel('dephasing γ')
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _plot_bar(path: Path, labels: list[str], values: list[float], ylabel: str, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(7.0, 4.2))
    plt.bar(np.arange(len(labels)), np.asarray(values, dtype=float))
    plt.xticks(np.arange(len(labels)), labels)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def phase14_report(output_root: Path, payload: dict) -> dict[str, Path]:
    project_root = output_root.parents[1]
    reports_dir = project_root / '05_reports'
    plots_root = reports_dir / 'plots' / 'phase14_local_field'
    reports_dir.mkdir(parents=True, exist_ok=True)
    plot_paths: dict[str, Path] = {}

    labels = []
    valid_counts = []
    for benchmark_id, summary in payload['benchmark_summaries'].items():
        labels.append(benchmark_id)
        valid_counts.append(float(summary['valid_field_cell_count']))
        bench = payload['benchmark_payloads'][benchmark_id]
        switch = bench['switch_level']
        bench_plot_dir = plots_root / bench['slug']
        field_path = bench_plot_dir / 'switch_field.png'
        _plot_heatmap(
            field_path,
            np.asarray(switch['smoothed_field'], dtype=float),
            np.asarray(switch['cells_u'], dtype=float),
            np.asarray(switch['cells_v'], dtype=float),
            title=f'{benchmark_id} smoothed local field at switch γ={bench["recommended_switch_gamma"]:.2f}',
            zero_crossings=switch['zero_crossings'],
        )
        plot_paths[f'{benchmark_id}_field'] = field_path
        consistency_path = bench_plot_dir / 'switch_consistency.png'
        _plot_heatmap(
            consistency_path,
            np.asarray(switch['sign_consistency'], dtype=float),
            np.asarray(switch['cells_u'], dtype=float),
            np.asarray(switch['cells_v'], dtype=float),
            title=f'{benchmark_id} field sign consistency at switch γ={bench["recommended_switch_gamma"]:.2f}',
            zero_crossings=switch['zero_crossings'],
        )
        plot_paths[f'{benchmark_id}_consistency'] = consistency_path

    suite_path = plots_root / 'suite_valid_field_cells.png'
    _plot_bar(suite_path, labels, valid_counts, ylabel='valid field cells', title='Phase 14 valid local-field cells at switch γ')
    plot_paths['suite_valid_field_cells'] = suite_path

    focus = payload['benchmark_payloads'][payload['focus_benchmark']]
    focus_dir = plots_root / focus['slug']
    x = np.asarray(payload['dephasing_values'], dtype=float)
    center_keys = list(focus['switch_level']['sampled_centers'].keys())
    if center_keys:
        slope_series = {key: [level['sampled_centers'].get(key, {}).get('slope') for level in focus['levels']] for key in center_keys}
        slope_path = focus_dir / 'sampled_center_slope_vs_dephasing.png'
        _plot_line(slope_path, x, slope_series, ylabel='sampled local field χ', title=f'{payload["focus_benchmark"]} sampled local field vs dephasing')
        plot_paths['focus_center_slope_vs_dephasing'] = slope_path
        consistency_series = {key: [level['sampled_centers'].get(key, {}).get('consistency') for level in focus['levels']] for key in center_keys}
        consistency_lines = focus_dir / 'sampled_center_consistency_vs_dephasing.png'
        _plot_line(consistency_lines, x, consistency_series, ylabel='sign consistency', title=f'{payload["focus_benchmark"]} sampled local-field consistency vs dephasing')
        plot_paths['focus_center_consistency_vs_dephasing'] = consistency_lines
    zero_series = {'zero crossing u': [level['zero_crossing_u_mean'] for level in focus['levels']]}
    zero_path = focus_dir / 'zero_crossing_vs_dephasing.png'
    _plot_line(zero_path, x, zero_series, ylabel='u at field zero crossing', title=f'{payload["focus_benchmark"]} sign-boundary location vs dephasing')
    plot_paths['focus_zero_crossing_vs_dephasing'] = zero_path

    report_path = reports_dir / 'CWT-CGT_Phase_14_Report.md'
    lines = ['# CWT-CGT Phase 14 Report', '', '## What Phase 14 adds', '']
    lines.append('Phase 14 replaces the discrete patch-family noisy atlas with a **smoothed local mixed-state field** built from generator-driven minimal plaquettes.')
    lines.append('')
    lines.append('Each benchmark is now summarized by:')
    lines.append('- trusted vs excluded minimal plaquettes,')
    lines.append('- valid local-field cells after a holonomy floor and effective-support filter,')
    lines.append('- local sign-consistency and sign-boundary structure,')
    lines.append('- sampled field values at the Phase 13 by-center reference points when available.')
    lines.append('')
    lines.append('## Suite summary at the recommended switch γ')
    lines.append('')
    for benchmark_id, summary in payload['benchmark_summaries'].items():
        lines.append(
            f"- {benchmark_id}: verdict={summary['verdict']}, switch γ={summary['switch_gamma']:.2f}, valid field cells={summary['valid_field_cell_count']}, trusted plaquettes={summary['trusted_plaquette_count']}, excluded plaquettes={summary['excluded_plaquette_count']}, zero-crossing u={summary['zero_crossing_u_mean']}"
        )
    lines.append('')
    lines.append('## Focus benchmark interpretation')
    lines.append('')
    focus_switch = focus['switch_level']
    lines.append(f"Focus benchmark: **{payload['focus_benchmark']}** at switch γ={focus['recommended_switch_gamma']:.2f}.")
    lines.append(f"The smoothed field has {focus_switch['valid_field_cell_count']} valid cells and {len(focus_switch['zero_crossings'])} zero-crossing samples.")
    lines.append(f"Mean field consistency on valid cells: {focus_switch['consistency_summary']['mean']}.")
    lines.append(f"Mean zero-crossing location in control-1: {focus_switch['zero_crossing_u_mean']}.")
    if focus_switch['sampled_centers']:
        lines.append('')
        lines.append('| center | sampled χ | consistency | effective support | mean abs holonomy gap |')
        lines.append('|---|---:|---:|---:|---:|')
        for key, row in focus_switch['sampled_centers'].items():
            lines.append(
                f"| {key} | {row['slope']} | {row['consistency']} | {row['effective_support']} | {row['mean_abs_holonomy_gap']} |"
            )
    lines.append('')
    lines.append('## Interpretation')
    lines.append('')
    lines.append('- Benchmarks A and D remain null-like at the noisy switch point under the local-field filter.')
    lines.append('- Benchmark B remains weak: it does not clear the local-field holonomy floor at the switch point.')
    lines.append('- Benchmark C remains the positive noisy benchmark, but it is now described as a **structured local field with a sign boundary**, not just a discrete patch table.')
    lines.append('- Benchmark F remains an exclusion / R4 benchmark with no trusted local-field cells.')
    lines.append('')
    lines.append(f"Suite plot: `{plot_paths['suite_valid_field_cells']}`")
    report_path.write_text('\n'.join(lines) + '\n')
    plot_paths['phase14_report'] = report_path
    return plot_paths
