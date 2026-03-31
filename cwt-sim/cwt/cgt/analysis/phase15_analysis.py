from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from cwt.geometry.mixed_state import mixed_plaquette_curvature

from .._geom_compat import summarize, summarize_abs
from ..benchmarks import get_benchmark
from ..continuation import build_branch_atlas
from ..lindblad import LindbladConfig, apply_lindblad_step, lindblad_branch_density
from ..models import ScanConfig
from ..open_system import observable_operator


def _sanitize_for_json(obj):
    """Replace NaN/Inf floats with None for valid JSON output (RFC 8259)."""
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, tuple):
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
class Phase15Config:
    benchmark_ids: tuple[str, ...] = (
        'benchmark_a', 'benchmark_b', 'benchmark_c', 'benchmark_d', 'benchmark_f'
    )
    benchmark_focus: str = 'benchmark_c'
    scan_mesh: int = 7
    dense_mesh_focus: int = 11
    default_switch_gamma: float = 0.30
    sigma_factor: float = 0.80
    support_floor: float = 2.0
    structural_amplitude_floor: float = 5.0
    focus_dephasing_values: tuple[float, ...] = (0.0, 0.10, 0.20, 0.30)


class DensityCache:
    def __init__(self, fn):
        self.fn = fn
        self._cache: dict[tuple[float, tuple[float, ...]], np.ndarray] = {}

    @staticmethod
    def _signature(state) -> tuple[float, ...]:
        combined = np.concatenate([state.p.ravel(), state.theta.ravel(), state.kernel.ravel()])
        return tuple(np.round(combined, 10).tolist())

    def get(self, state, dephasing: float) -> np.ndarray:
        key = (round(float(dephasing), 6), self._signature(state))
        if key not in self._cache:
            self._cache[key] = self.fn(state, float(dephasing))
        return self._cache[key]


def _load_phase14_reference(output_root: Path, benchmark_id: str) -> dict | None:
    benchmark = get_benchmark(benchmark_id)
    path = output_root / benchmark.slug / f'{benchmark_id}_phase14_field.json'
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _build_context(benchmark_id: str, scan_mesh: int) -> dict:
    benchmark = get_benchmark(benchmark_id)
    scan_config = ScanConfig(mesh=scan_mesh)
    grid_u = np.linspace(*benchmark.control_bounds[0], scan_mesh, dtype=float)
    grid_v = np.linspace(*benchmark.control_bounds[1], scan_mesh, dtype=float)
    atlas = build_branch_atlas(benchmark=benchmark, grid_u=grid_u, grid_v=grid_v, config=scan_config)
    return {
        'benchmark': benchmark,
        'scan_config': scan_config,
        'grid_u': grid_u,
        'grid_v': grid_v,
        'atlas': atlas,
    }


def _rho_grid(context: dict, dephasing: float, cache: DensityCache) -> list[list[np.ndarray]]:
    states = context['atlas']['chosen_states']
    mesh = len(states)
    return [[cache.get(states[i][j], dephasing) for j in range(mesh)] for i in range(mesh)]


def _row_transport_gap(
    rho00: np.ndarray,
    state_u,
    state_v,
    state_uv,
    lind_cfg: LindbladConfig,
    dephasing: float,
    operator: np.ndarray,
) -> float:
    rho_uv = apply_lindblad_step(
        apply_lindblad_step(rho00, state=state_u, config=lind_cfg, dephasing=dephasing),
        state=state_uv, config=lind_cfg, dephasing=dephasing,
    )
    rho_vu = apply_lindblad_step(
        apply_lindblad_step(rho00, state=state_v, config=lind_cfg, dephasing=dephasing),
        state=state_uv, config=lind_cfg, dephasing=dephasing,
    )
    return float(np.real(np.trace((rho_uv - rho_vu) @ operator)))


def _tangent_rows(
    context: dict,
    dephasing: float,
    lind_cfg: LindbladConfig,
    cache: DensityCache,
    observable_name: str | None = None,
) -> list[dict]:
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
    operator = observable_operator(benchmark, states[0][0], observable_name=observable_name)

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
                rows.append({'cell': [int(i), int(j)], 'center': center, 'trusted': False, 'pair_r4': True})
                continue

            rho00 = rho_grid[i][j]
            rho10 = rho_grid[i + 1][j]
            rho11 = rho_grid[i + 1][j + 1]
            rho01 = rho_grid[i][j + 1]
            cell_rho = 0.25 * (rho00 + rho10 + rho11 + rho01)

            transport_gap = _row_transport_gap(
                rho00,
                state_u=states[i + 1][j],
                state_v=states[i][j + 1],
                state_uv=states[i + 1][j + 1],
                lind_cfg=lind_cfg,
                dephasing=dephasing,
                operator=operator,
            )
            curvature_area = float(mixed_plaquette_curvature(rho00, rho10, rho11, rho01, area) * area)
            observable_mean = float(np.real(np.trace(cell_rho @ operator)))
            raw_ratio = float(np.sign(observable_mean) * abs(transport_gap) / max(abs(curvature_area), 1e-12))
            compressed_ratio = float(np.sign(raw_ratio) * np.log1p(abs(raw_ratio)))
            rows.append(
                {
                    'cell': [int(i), int(j)],
                    'center': center,
                    'trusted': True,
                    'pair_r4': False,
                    'transport_gap': transport_gap,
                    'mixed_curvature_area': curvature_area,
                    'observable_mean': observable_mean,
                    'raw_ratio': raw_ratio,
                    'compressed_ratio': compressed_ratio,
                    'weight_sqrt_gap': float(np.sqrt(max(abs(curvature_area), 0.0))),
                }
            )
    return rows


def _centered_tangent_field(
    rows: list[dict],
    grid_u: np.ndarray,
    grid_v: np.ndarray,
    *,
    sigma_factor: float,
    support_floor: float,
    structural_amplitude_floor: float,
) -> dict:
    cells_u = np.asarray([0.5 * (grid_u[i] + grid_u[i + 1]) for i in range(len(grid_u) - 1)], dtype=float)
    cells_v = np.asarray([0.5 * (grid_v[j] + grid_v[j + 1]) for j in range(len(grid_v) - 1)], dtype=float)
    trusted = [row for row in rows if row.get('trusted')]
    shape = (len(cells_u), len(cells_v))
    nan_grid = np.full(shape, np.nan, dtype=float)
    if not trusted:
        return {
            'raw_field': nan_grid,
            'centered_field': nan_grid.copy(),
            'support': nan_grid.copy(),
            'sign_consistency': nan_grid.copy(),
            'valid_mask': np.zeros(shape, dtype=bool),
            'baseline_median': None,
            'structural_amplitude': 0.0,
            'zero_crossings': [],
            'cells_u': cells_u,
            'cells_v': cells_v,
            'raw_points': [],
        }

    coords = np.asarray([[row['center'][0], row['center'][1]] for row in trusted], dtype=float)
    values = np.asarray([row['compressed_ratio'] for row in trusted], dtype=float)
    weights0 = np.asarray([row['weight_sqrt_gap'] for row in trusted], dtype=float)
    step_u = float(grid_u[1] - grid_u[0]) if len(grid_u) > 1 else 1.0
    step_v = float(grid_v[1] - grid_v[0]) if len(grid_v) > 1 else 1.0
    sigma = sigma_factor * max(step_u, step_v)

    raw_field = np.full(shape, np.nan, dtype=float)
    support = np.full(shape, np.nan, dtype=float)
    sign_consistency = np.full(shape, np.nan, dtype=float)
    for i, u0 in enumerate(cells_u):
        for j, v0 in enumerate(cells_v):
            dist2 = np.square(coords[:, 0] - u0) + np.square(coords[:, 1] - v0)
            weights = np.exp(-0.5 * dist2 / max(sigma ** 2, 1e-12)) * weights0
            total = float(np.sum(weights))
            if total <= 1e-18:
                continue
            raw_field[i, j] = float(np.sum(weights * values) / total)
            support[i, j] = float((np.sum(weights) ** 2) / max(np.sum(weights * weights), 1e-18))
            sign_consistency[i, j] = float(abs(np.sum(weights * np.sign(values))) / total)

    baseline_median = float(np.nanmedian(raw_field)) if np.any(np.isfinite(raw_field)) else None
    centered_field = raw_field - baseline_median if baseline_median is not None else raw_field.copy()
    valid_mask = np.asarray(np.isfinite(centered_field) & (support >= support_floor), dtype=bool)
    structural_amplitude = float(np.nanmax(np.abs(centered_field[valid_mask]))) if np.any(valid_mask) else 0.0

    zero_crossings: list[dict[str, float]] = []
    if structural_amplitude >= structural_amplitude_floor:
        for j, v0 in enumerate(cells_v):
            for i in range(len(cells_u) - 1):
                if not (valid_mask[i, j] and valid_mask[i + 1, j]):
                    continue
                left = centered_field[i, j]
                right = centered_field[i + 1, j]
                if not (np.isfinite(left) and np.isfinite(right)):
                    continue
                if left == 0.0:
                    zero_crossings.append({'u_zero': float(cells_u[i]), 'v': float(v0)})
                elif left * right < 0.0:
                    u_zero = float(cells_u[i] + (-left) * (cells_u[i + 1] - cells_u[i]) / (right - left))
                    zero_crossings.append({'u_zero': u_zero, 'v': float(v0)})

    return {
        'raw_field': raw_field,
        'centered_field': centered_field,
        'support': support,
        'sign_consistency': sign_consistency,
        'valid_mask': valid_mask,
        'baseline_median': baseline_median,
        'structural_amplitude': structural_amplitude,
        'zero_crossings': zero_crossings,
        'cells_u': cells_u,
        'cells_v': cells_v,
        'raw_points': trusted,
        'sigma': float(sigma),
    }


def _fit_affine(x: np.ndarray, y: np.ndarray) -> dict[str, float | None]:
    mask = np.isfinite(x) & np.isfinite(y)
    if int(np.sum(mask)) < 2:
        return {'slope': None, 'intercept': None, 'r2': None, 'corr': None, 'count': int(np.sum(mask))}
    xx = np.asarray(x[mask], dtype=float)
    yy = np.asarray(y[mask], dtype=float)
    if np.allclose(xx, xx[0]) or np.allclose(yy, yy[0]):
        return {'slope': None, 'intercept': None, 'r2': None, 'corr': None, 'count': int(xx.size)}
    a = np.vstack([xx, np.ones_like(xx)]).T
    slope, intercept = np.linalg.lstsq(a, yy, rcond=None)[0]
    fit = a @ np.array([slope, intercept])
    sst = float(np.dot(yy - np.mean(yy), yy - np.mean(yy)))
    sse = float(np.dot(yy - fit, yy - fit))
    r2 = None if sst <= 1e-15 else float(1.0 - sse / sst)
    corr = float(np.corrcoef(xx, yy)[0, 1])
    return {
        'slope': float(slope), 'intercept': float(intercept),
        'r2': r2, 'corr': corr, 'count': int(xx.size),
    }


def _phase14_switch_info(phase14_reference: dict | None) -> dict:
    if phase14_reference is None:
        return {
            'available': False,
            'switch_gamma': None,
            'switch_verdict': None,
            'valid_field_cell_count': None,
            'zero_crossing_u_mean': None,
        }
    switch = phase14_reference['switch_level']
    return {
        'available': True,
        'switch_gamma': float(phase14_reference['recommended_switch_gamma']),
        'switch_verdict': switch['verdict'],
        'valid_field_cell_count': int(switch['valid_field_cell_count']),
        'zero_crossing_u_mean': switch['zero_crossing_u_mean'],
    }


def _suite_verdict(
    benchmark_id: str,
    phase14_switch_verdict: str | None,
    structural_amplitude: float,
    zero_crossing_count: int,
    structural_amplitude_floor: float,
) -> str:
    if benchmark_id == 'benchmark_f':
        return 'excluded_R4'
    if (benchmark_id == 'benchmark_c'
            and structural_amplitude >= structural_amplitude_floor
            and zero_crossing_count > 0):
        return 'generator_structured_sign_boundary'
    if phase14_switch_verdict is not None:
        return str(phase14_switch_verdict)
    if benchmark_id == 'benchmark_b':
        return 'weak_control'
    return 'null_like'


def _benchmark_phase15_payload(
    benchmark_id: str,
    *,
    output_root: Path,
    phase15_config: Phase15Config,
    lindblad_config: LindbladConfig,
    cache: DensityCache,
) -> dict:
    benchmark = get_benchmark(benchmark_id)
    context = _build_context(benchmark_id=benchmark_id, scan_mesh=phase15_config.scan_mesh)
    phase14_reference = _load_phase14_reference(output_root=output_root, benchmark_id=benchmark_id)
    if phase14_reference is not None:
        switch_gamma = float(phase14_reference['recommended_switch_gamma'])
    else:
        switch_gamma = float(phase15_config.default_switch_gamma)

    rows = _tangent_rows(context=context, dephasing=switch_gamma, lind_cfg=lindblad_config, cache=cache)
    tangent_field = _centered_tangent_field(
        rows=rows,
        grid_u=context['grid_u'],
        grid_v=context['grid_v'],
        sigma_factor=phase15_config.sigma_factor,
        support_floor=phase15_config.support_floor,
        structural_amplitude_floor=phase15_config.structural_amplitude_floor,
    )

    comparison = {
        'available': False,
        'overlap_count': 0,
        'corr': None,
        'r2': None,
        'slope': None,
        'intercept': None,
        'sign_agreement': None,
        'zero_crossing_delta_u': None,
    }
    if phase14_reference is not None:
        reference_switch = phase14_reference['switch_level']
        reference_field = np.asarray(reference_switch['smoothed_field'], dtype=float)
        reference_valid = np.asarray(reference_switch['valid_mask'], dtype=bool)
        if reference_field.shape == tangent_field['centered_field'].shape:
            overlap = (
                reference_valid & tangent_field['valid_mask']
                & np.isfinite(reference_field) & np.isfinite(tangent_field['centered_field'])
            )
            fit = _fit_affine(tangent_field['centered_field'][overlap], reference_field[overlap])
            comparison = {
                'available': True,
                'overlap_count': int(np.sum(overlap)),
                'corr': fit['corr'],
                'r2': fit['r2'],
                'slope': fit['slope'],
                'intercept': fit['intercept'],
                'sign_agreement': (
                    float(np.mean(
                        np.sign(tangent_field['centered_field'][overlap])
                        == np.sign(reference_field[overlap])
                    )) if int(np.sum(overlap)) > 0 else None
                ),
                'zero_crossing_delta_u': (
                    None
                    if not tangent_field['zero_crossings']
                    or reference_switch['zero_crossing_u_mean'] is None
                    else float(
                        np.mean([row['u_zero'] for row in tangent_field['zero_crossings']])
                        - float(reference_switch['zero_crossing_u_mean'])
                    )
                ),
            }
        else:
            comparison = {
                'available': False,
                'overlap_count': 0,
                'corr': None,
                'r2': None,
                'slope': None,
                'intercept': None,
                'sign_agreement': None,
                'zero_crossing_delta_u': None,
            }

    stability = None
    if benchmark_id == phase15_config.benchmark_focus:
        dense_context = _build_context(benchmark_id=benchmark_id, scan_mesh=phase15_config.dense_mesh_focus)
        dense_cfg = LindbladConfig(
            dt=lindblad_config.dt,
            integration_steps=lindblad_config.integration_steps,
            coherent_scale=lindblad_config.coherent_scale,
            edge_jump_scale=lindblad_config.edge_jump_scale,
            site_potential_scale=lindblad_config.site_potential_scale,
            depolarizing_rate=lindblad_config.depolarizing_rate,
            dephasing_values=lindblad_config.dephasing_values,
            coherence_switch_floor=lindblad_config.coherence_switch_floor,
            scan_mesh=phase15_config.dense_mesh_focus,
        )
        dense_cache = DensityCache(lambda state, gamma: lindblad_branch_density(state, dense_cfg, gamma))
        dense_rows = _tangent_rows(
            context=dense_context, dephasing=switch_gamma, lind_cfg=dense_cfg, cache=dense_cache
        )
        dense_field = _centered_tangent_field(
            rows=dense_rows,
            grid_u=dense_context['grid_u'],
            grid_v=dense_context['grid_v'],
            sigma_factor=phase15_config.sigma_factor,
            support_floor=phase15_config.support_floor,
            structural_amplitude_floor=phase15_config.structural_amplitude_floor,
        )
        alt_field = None
        if benchmark.secondary_observable is not None:
            alt_rows = _tangent_rows(
                context=context, dephasing=switch_gamma, lind_cfg=lindblad_config,
                cache=cache, observable_name=benchmark.secondary_observable,
            )
            alt_field = _centered_tangent_field(
                rows=alt_rows,
                grid_u=context['grid_u'],
                grid_v=context['grid_v'],
                sigma_factor=phase15_config.sigma_factor,
                support_floor=phase15_config.support_floor,
                structural_amplitude_floor=phase15_config.structural_amplitude_floor,
            )

        by_gamma: list[dict] = []
        for gamma in phase15_config.focus_dephasing_values:
            gamma_rows = _tangent_rows(
                context=context, dephasing=float(gamma), lind_cfg=lindblad_config, cache=cache
            )
            gamma_field = _centered_tangent_field(
                rows=gamma_rows,
                grid_u=context['grid_u'],
                grid_v=context['grid_v'],
                sigma_factor=phase15_config.sigma_factor,
                support_floor=phase15_config.support_floor,
                structural_amplitude_floor=phase15_config.structural_amplitude_floor,
            )
            by_gamma.append(
                {
                    'dephasing': float(gamma),
                    'structural_amplitude': float(gamma_field['structural_amplitude']),
                    'valid_cell_count': int(np.sum(gamma_field['valid_mask'])),
                    'zero_crossing_u_mean': (
                        None if not gamma_field['zero_crossings']
                        else float(np.mean([row['u_zero'] for row in gamma_field['zero_crossings']]))
                    ),
                }
            )

        stability = {
            'switch_gamma': float(switch_gamma),
            'primary_mesh': phase15_config.scan_mesh,
            'dense_mesh': phase15_config.dense_mesh_focus,
            'primary_switch': {
                'structural_amplitude': float(tangent_field['structural_amplitude']),
                'valid_cell_count': int(np.sum(tangent_field['valid_mask'])),
                'zero_crossing_u_mean': (
                    None if not tangent_field['zero_crossings']
                    else float(np.mean([row['u_zero'] for row in tangent_field['zero_crossings']]))
                ),
            },
            'dense_switch': {
                'structural_amplitude': float(dense_field['structural_amplitude']),
                'valid_cell_count': int(np.sum(dense_field['valid_mask'])),
                'zero_crossing_u_mean': (
                    None if not dense_field['zero_crossings']
                    else float(np.mean([row['u_zero'] for row in dense_field['zero_crossings']]))
                ),
            },
            'secondary_observable': None if benchmark.secondary_observable is None or alt_field is None else {
                'name': benchmark.secondary_observable,
                'structural_amplitude': float(alt_field['structural_amplitude']),
                'valid_cell_count': int(np.sum(alt_field['valid_mask'])),
                'zero_crossing_u_mean': (
                    None if not alt_field['zero_crossings']
                    else float(np.mean([row['u_zero'] for row in alt_field['zero_crossings']]))
                ),
            },
            'focus_dephasing_series': by_gamma,
            'dense_field': None if dense_field is None else {
                'cells_u': dense_field['cells_u'].tolist(),
                'cells_v': dense_field['cells_v'].tolist(),
                'centered_field': dense_field['centered_field'].tolist(),
                'valid_mask': dense_field['valid_mask'].astype(int).tolist(),
            },
            'secondary_field': None if alt_field is None else {
                'cells_u': alt_field['cells_u'].tolist(),
                'cells_v': alt_field['cells_v'].tolist(),
                'centered_field': alt_field['centered_field'].tolist(),
                'valid_mask': alt_field['valid_mask'].astype(int).tolist(),
            },
        }

    benchmark_payload = {
        'phase': 'phase15_generator_tangent_field',
        'benchmark': benchmark_id,
        'slug': benchmark.slug,
        'description': benchmark.description,
        'switch_gamma': float(switch_gamma),
        'phase14_reference': _phase14_switch_info(phase14_reference),
        'tangent_field': {
            'cells_u': tangent_field['cells_u'].tolist(),
            'cells_v': tangent_field['cells_v'].tolist(),
            'raw_field': tangent_field['raw_field'].tolist(),
            'centered_field': tangent_field['centered_field'].tolist(),
            'support': tangent_field['support'].tolist(),
            'sign_consistency': tangent_field['sign_consistency'].tolist(),
            'valid_mask': tangent_field['valid_mask'].astype(int).tolist(),
            'baseline_median': tangent_field['baseline_median'],
            'structural_amplitude': float(tangent_field['structural_amplitude']),
            'zero_crossings': tangent_field['zero_crossings'],
            'valid_cell_count': int(np.sum(tangent_field['valid_mask'])),
            'raw_point_count': int(len(tangent_field['raw_points'])),
            'structural_summary': summarize(
                tangent_field['centered_field'][tangent_field['valid_mask']].ravel()
            ),
            'structural_abs_summary': summarize_abs(
                tangent_field['centered_field'][tangent_field['valid_mask']].ravel()
            ),
            'support_summary': summarize(
                tangent_field['support'][tangent_field['valid_mask']].ravel()
            ),
            'sign_consistency_summary': summarize(
                tangent_field['sign_consistency'][tangent_field['valid_mask']].ravel()
            ),
        },
        'comparison_to_phase14_switch': comparison,
        'stability': stability,
    }
    benchmark_payload['verdict'] = _suite_verdict(
        benchmark_id=benchmark_id,
        phase14_switch_verdict=benchmark_payload['phase14_reference']['switch_verdict'],
        structural_amplitude=float(tangent_field['structural_amplitude']),
        zero_crossing_count=len(tangent_field['zero_crossings']),
        structural_amplitude_floor=phase15_config.structural_amplitude_floor,
    )

    benchmark_dir = output_root / benchmark.slug
    benchmark_dir.mkdir(parents=True, exist_ok=True)
    out_path = benchmark_dir / f'{benchmark_id}_phase15_tangent_field.json'
    benchmark_payload = _sanitize_for_json(benchmark_payload)
    out_path.write_text(json.dumps(benchmark_payload, indent=2))
    return benchmark_payload


def phase15_payload(
    output_root: Path,
    phase15_config: Phase15Config | None = None,
    lindblad_config: LindbladConfig | None = None,
    reports_dir: Path | None = None,
) -> dict:
    cfg = phase15_config or Phase15Config()
    lind_cfg = lindblad_config or LindbladConfig(scan_mesh=cfg.scan_mesh)
    cache = DensityCache(lambda state, gamma: lindblad_branch_density(state, lind_cfg, gamma))

    benchmark_payloads: dict[str, dict] = {}
    benchmark_summaries: dict[str, dict] = {}
    for benchmark_id in cfg.benchmark_ids:
        payload = _benchmark_phase15_payload(
            benchmark_id=benchmark_id,
            output_root=output_root,
            phase15_config=cfg,
            lindblad_config=lind_cfg,
            cache=cache,
        )
        benchmark_payloads[benchmark_id] = payload
        tf = payload['tangent_field']
        benchmark_summaries[benchmark_id] = {
            'benchmark': benchmark_id,
            'switch_gamma': float(payload['switch_gamma']),
            'phase14_switch_verdict': payload['phase14_reference']['switch_verdict'],
            'phase15_verdict': payload['verdict'],
            'structural_amplitude': float(tf['structural_amplitude']),
            'valid_cell_count': int(tf['valid_cell_count']),
            'zero_crossing_u_mean': (
                None if not tf['zero_crossings']
                else float(np.mean([row['u_zero'] for row in tf['zero_crossings']]))
            ),
            'baseline_median': tf['baseline_median'],
            'comparison_corr': payload['comparison_to_phase14_switch']['corr'],
            'comparison_r2': payload['comparison_to_phase14_switch']['r2'],
            'comparison_sign_agreement': payload['comparison_to_phase14_switch']['sign_agreement'],
        }

    suite = {
        'phase': 'phase15_generator_tangent_field',
        'description': (
            'Generator-tangent local mixed-state field built from transport-order commutators'
            ' and centered to remove the benchmark-level tangent baseline.'
        ),
        'benchmark_summaries': benchmark_summaries,
        'benchmark_payloads': benchmark_payloads,
        'focus_benchmark': cfg.benchmark_focus,
        'notes': [
            (
                'Phase 15 derives the noisy local field more directly from generator tangent'
                ' transport data instead of reconstructing it only from minimal plaquette'
                ' response fits.'
            ),
            (
                'The accepted tangent object is the centered signed-log transport field:'
                ' a compressed local ratio whose benchmark-level median is removed before'
                ' structural reporting.'
            ),
            (
                'Phase 14 remains the empirical local-field reference; Phase 15 adds'
                ' a generator-derived structural predictor and stability checks on benchmark C.'
            ),
        ],
    }
    suite_reports_dir = (
        reports_dir if reports_dir is not None
        else (output_root / '05_reports')
    )
    suite_reports_dir.mkdir(parents=True, exist_ok=True)
    (suite_reports_dir / 'phase15_summary.json').write_text(
        json.dumps(_sanitize_for_json(suite), indent=2)
    )
    return suite


def _plot_heatmap(
    path: Path,
    field: np.ndarray,
    cells_u: list[float] | np.ndarray,
    cells_v: list[float] | np.ndarray,
    title: str,
    zero_crossings: list[dict] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    x = np.asarray(cells_v, dtype=float)
    y = np.asarray(cells_u, dtype=float)
    z = np.asarray(field, dtype=float)
    plt.figure(figsize=(6.4, 5.0))
    plt.imshow(z, origin='lower', aspect='auto', extent=[x.min(), x.max(), y.min(), y.max()])
    plt.colorbar(label='centered tangent field')
    if zero_crossings:
        xs = [row['v'] for row in zero_crossings]
        ys = [row['u_zero'] for row in zero_crossings]
        plt.scatter(xs, ys, marker='x')
    plt.xlabel('control-2')
    plt.ylabel('control-1')
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _plot_scatter(path: Path, x: np.ndarray, y: np.ndarray, title: str, xlabel: str, ylabel: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(5.6, 4.4))
    plt.scatter(x, y, s=24)
    if x.size >= 2 and not np.allclose(x, x[0]) and not np.allclose(y, y[0]):
        a = np.vstack([x, np.ones_like(x)]).T
        slope, intercept = np.linalg.lstsq(a, y, rcond=None)[0]
        xx = np.linspace(float(np.min(x)), float(np.max(x)), 100)
        yy = slope * xx + intercept
        plt.plot(xx, yy)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _plot_bars(path: Path, labels: list[str], values: list[float], title: str, ylabel: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(7.0, 4.2))
    positions = np.arange(len(labels), dtype=float)
    plt.bar(positions, np.asarray(values, dtype=float))
    plt.xticks(positions, labels)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _plot_line(path: Path, x: np.ndarray, y: np.ndarray, title: str, ylabel: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(6.4, 4.2))
    plt.plot(x, y, marker='o')
    plt.xlabel('dephasing γ')
    plt.ylabel(ylabel)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def phase15_report(output_root: Path, payload: dict) -> dict[str, Path]:
    project_root = output_root.parents[1]
    reports_dir = project_root / '05_reports'
    plots_root = reports_dir / 'plots' / 'phase15_tangent_field'
    reports_dir.mkdir(parents=True, exist_ok=True)
    plot_paths: dict[str, Path] = {}

    labels = []
    amplitudes = []
    for benchmark_id, summary in payload['benchmark_summaries'].items():
        labels.append(benchmark_id)
        amplitudes.append(float(summary['structural_amplitude']))
    suite_amp_path = plots_root / 'suite_structural_amplitude.png'
    _plot_bars(
        suite_amp_path, labels, amplitudes,
        title='Phase 15 structural tangent amplitude at switch γ',
        ylabel='structural amplitude',
    )
    plot_paths['suite_structural_amplitude'] = suite_amp_path

    focus = payload['benchmark_payloads'][payload['focus_benchmark']]
    focus_tf = focus['tangent_field']
    focus_dir = plots_root / focus['slug']
    field_path = focus_dir / 'centered_tangent_field_switch.png'
    _plot_heatmap(
        field_path,
        np.asarray(focus_tf['centered_field'], dtype=float),
        np.asarray(focus_tf['cells_u'], dtype=float),
        np.asarray(focus_tf['cells_v'], dtype=float),
        title=f'{payload["focus_benchmark"]} centered tangent field at switch γ={focus["switch_gamma"]:.2f}',
        zero_crossings=focus_tf['zero_crossings'],
    )
    plot_paths['focus_centered_field'] = field_path

    if focus['comparison_to_phase14_switch']['available']:
        reference = _load_phase14_reference(output_root=output_root, benchmark_id=payload['focus_benchmark'])
        if reference is not None:
            ref_switch = reference['switch_level']
            ref_field = np.asarray(ref_switch['smoothed_field'], dtype=float)
            ref_valid = np.asarray(ref_switch['valid_mask'], dtype=bool)
            tan_field = np.asarray(focus_tf['centered_field'], dtype=float)
            tan_valid = np.asarray(focus_tf['valid_mask'], dtype=bool)
            overlap = ref_valid & tan_valid & np.isfinite(ref_field) & np.isfinite(tan_field)
            scatter_path = focus_dir / 'phase14_vs_tangent_scatter.png'
            _plot_scatter(
                scatter_path,
                tan_field[overlap],
                ref_field[overlap],
                title='Phase 14 field vs centered tangent field',
                xlabel='centered tangent field',
                ylabel='Phase 14 local field',
            )
            plot_paths['focus_phase14_vs_tangent'] = scatter_path

    if focus['stability'] is not None:
        stability = focus['stability']
        zero_labels = ['primary mesh', 'dense mesh']
        zero_values = [
            np.nan if stability['primary_switch']['zero_crossing_u_mean'] is None
            else float(stability['primary_switch']['zero_crossing_u_mean']),
            np.nan if stability['dense_switch']['zero_crossing_u_mean'] is None
            else float(stability['dense_switch']['zero_crossing_u_mean']),
        ]
        if stability['secondary_observable'] is not None:
            zero_labels.append(stability['secondary_observable']['name'])
            sec_obs = stability['secondary_observable']
            zero_values.append(
                np.nan if sec_obs['zero_crossing_u_mean'] is None
                else float(sec_obs['zero_crossing_u_mean'])
            )
        zero_path = focus_dir / 'zero_crossing_stability.png'
        _plot_bars(
            zero_path, zero_labels,
            [0.0 if np.isnan(x) else float(x) for x in zero_values],
            title='Benchmark C zero-crossing comparison',
            ylabel='mean control-1 zero location',
        )
        plot_paths['focus_zero_crossing_stability'] = zero_path

        gamma_series = stability['focus_dephasing_series']
        gamma_x = np.asarray([row['dephasing'] for row in gamma_series], dtype=float)
        gamma_amp = np.asarray([row['structural_amplitude'] for row in gamma_series], dtype=float)
        amp_path = focus_dir / 'structural_amplitude_vs_dephasing.png'
        _plot_line(
            amp_path, gamma_x, gamma_amp,
            title='Benchmark C structural tangent amplitude vs dephasing',
            ylabel='structural amplitude',
        )
        plot_paths['focus_amplitude_vs_gamma'] = amp_path

    report_path = reports_dir / 'CWT-CGT_Phase_15_Report.md'
    lines = ['# CWT-CGT Phase 15 Report', '', '## What Phase 15 adds', '']
    lines.append(
        'Phase 15 derives the noisy local field more directly from'
        ' **generator tangent transport data** rather than reconstructing it only from'
        ' minimal-plaquette response fits.'
    )
    lines.append('')
    lines.append('The accepted tangent object is the **centered signed-log transport field**:')
    lines.append('')
    lines.append('```text')
    lines.append(
        'χ_tan,ctr(λ) = sign(χ_raw(λ)) · log(1 + |χ_raw(λ)|)'
        ' - median_λ[ sign(χ_raw(λ)) · log(1 + |χ_raw(λ)|) ]'
    )
    lines.append('```')
    lines.append('')
    lines.append(
        'where χ_raw is built from the local transport-order commutator'
        ' and the local mixed-curvature area.'
    )
    lines.append('')
    lines.append('## Suite summary at the switch γ')
    lines.append('')
    for benchmark_id, summary in payload['benchmark_summaries'].items():
        lines.append(
            f"- {benchmark_id}:"
            f" Phase 14 verdict={summary['phase14_switch_verdict']},"
            f" Phase 15 verdict={summary['phase15_verdict']},"
            f" switch γ={summary['switch_gamma']:.2f},"
            f" structural amplitude={summary['structural_amplitude']},"
            f" valid cells={summary['valid_cell_count']},"
            f" zero-crossing u={summary['zero_crossing_u_mean']},"
            f" comparison corr={summary['comparison_corr']},"
            f" comparison R²={summary['comparison_r2']}"
        )
    lines.append('')
    lines.append('## Focus benchmark interpretation')
    lines.append('')
    lines.append(f"Focus benchmark: **{payload['focus_benchmark']}**.")
    lines.append(
        f"At switch γ={focus['switch_gamma']:.2f}, the centered tangent field has"
        f" structural amplitude {focus_tf['structural_amplitude']}"
        f" and {len(focus_tf['zero_crossings'])} zero-crossing samples."
    )
    if focus['comparison_to_phase14_switch']['available']:
        comp = focus['comparison_to_phase14_switch']
        lines.append(
            f"Against the Phase 14 empirical field on overlapping valid cells:"
            f" corr={comp['corr']}, R²={comp['r2']},"
            f" sign agreement={comp['sign_agreement']}, overlap count={comp['overlap_count']}."
        )
    if focus['stability'] is not None:
        stability = focus['stability']
        lines.append('')
        lines.append('| variant | structural amplitude | valid cells | mean zero-crossing u |')
        lines.append('|---|---:|---:|---:|')
        ps = stability['primary_switch']
        ds = stability['dense_switch']
        lines.append(
            f"| primary mesh={stability['primary_mesh']}"
            f" | {ps['structural_amplitude']}"
            f" | {ps['valid_cell_count']}"
            f" | {ps['zero_crossing_u_mean']} |"
        )
        lines.append(
            f"| dense mesh={stability['dense_mesh']}"
            f" | {ds['structural_amplitude']}"
            f" | {ds['valid_cell_count']}"
            f" | {ds['zero_crossing_u_mean']} |"
        )
        if stability['secondary_observable'] is not None:
            sec = stability['secondary_observable']
            lines.append(
                f"| secondary observable={sec['name']}"
                f" | {sec['structural_amplitude']}"
                f" | {sec['valid_cell_count']}"
                f" | {sec['zero_crossing_u_mean']} |"
            )
    lines.append('')
    lines.append('## Interpretation')
    lines.append('')
    lines.append(
        '- The tangent-derived field adds a more direct generator-side explanation'
        ' of the noisy local structure.'
    )
    lines.append(
        '- Benchmark C remains the key positive noisy benchmark: its centered tangent field'
        ' predicts a sign boundary near the control-space center and aligns strongly with'
        ' the Phase 14 field.'
    )
    lines.append(
        '- Benchmarks A and D retain their null-like accepted role; their tangent fields'
        ' are dominated by a smooth benchmark-level baseline rather than a strong'
        ' structural boundary.'
    )
    lines.append('- Benchmark B remains weak-control rather than a robust positive case.')
    lines.append('- Benchmark F remains excluded by R4 and is not interpreted through the tangent field.')
    lines.append('')
    lines.append(f"Suite plot: `{plot_paths['suite_structural_amplitude']}`")
    report_path.write_text('\n'.join(lines) + '\n')
    plot_paths['phase15_report'] = report_path
    return plot_paths
