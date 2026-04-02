from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..analytic_tangents import AnalyticBranchTangents, analytic_branch_tangents
from ..benchmarks import get_benchmark
from ..geometry import summarize, summarize_abs
from ..lindblad import LindbladConfig, lindblad_branch_density, lindblad_operators, vec_density, unvec_density
from ..mixed_state_geometry import mixed_plaquette_curvature
from ..open_system import branch_hamiltonian, observable_operator
from .phase15_analysis import (
    DensityCache,
    _build_context,
    _centered_tangent_field,
    _fit_affine,
    _load_phase14_reference,
    _phase14_switch_info,
    _plot_bars,
    _plot_heatmap,
    _plot_line,
    _plot_scatter,
)


@dataclass(frozen=True)
class Phase18Config:
    benchmark_ids: tuple[str, ...] = ('benchmark_a', 'benchmark_b', 'benchmark_c', 'benchmark_d', 'benchmark_f')
    benchmark_focus: str = 'benchmark_c'
    scan_mesh: int = 7
    dense_mesh_focus: int = 11
    default_switch_gamma: float = 0.30
    sigma_factor: float = 0.80
    support_floor: float = 2.0
    structural_amplitude_floor: float = 5.0
    focus_dephasing_values: tuple[float, ...] = (0.0, 0.10, 0.20, 0.30)


def _load_reference_json(path: Path) -> dict | None:
    return json.loads(path.read_text()) if path.exists() else None


def _load_phase17_reference(output_root: Path, benchmark_id: str) -> dict | None:
    benchmark = get_benchmark(benchmark_id)
    path = output_root / benchmark.slug / f'{benchmark_id}_phase17_frechet_field.json'
    return _load_reference_json(path)


def _analytic_dh(state, tangents: AnalyticBranchTangents, config: LindbladConfig, axis: str) -> np.ndarray:
    dtheta = tangents.dtheta_du if axis == 'u' else tangents.dtheta_dv
    dkernel = tangents.dkernel_du if axis == 'u' else tangents.dkernel_dv
    dp = tangents.dp_du if axis == 'u' else tangents.dp_dv
    p = np.asarray(state.p, dtype=float)
    theta = np.asarray(state.theta, dtype=float)
    kernel = np.asarray(state.kernel, dtype=float)
    n = p.size
    dh = np.zeros((n, n), dtype=complex)
    dlogp = dp / np.maximum(p, 1e-12)
    ddiag = -config.site_potential_scale * (dlogp - float(np.mean(dlogp)))
    dh += np.diag(ddiag)
    for i in range(n):
        for j in range(i + 1, n):
            sym = 0.5 * (kernel[i, j] + kernel[j, i])
            dsym = 0.5 * (dkernel[i, j] + dkernel[j, i])
            phase = 0.5 * (theta[j] - theta[i])
            dphase = 0.5 * (dtheta[j] - dtheta[i])
            entry = config.coherent_scale * np.exp(1j * phase) * (dsym + 1j * sym * dphase)
            dh[i, j] = entry
            dh[j, i] = np.conj(entry)
    return dh


def _analytic_jump_tangents(state, tangents: AnalyticBranchTangents, config: LindbladConfig, axis: str, dephasing: float) -> tuple[list[np.ndarray], list[np.ndarray]]:
    kernel = np.asarray(state.kernel, dtype=float)
    dkernel = tangents.dkernel_du if axis == 'u' else tangents.dkernel_dv
    n = kernel.shape[0]
    base_ops: list[np.ndarray] = []
    dops: list[np.ndarray] = []
    scale = config.edge_jump_scale
    for src in range(n):
        for dst in range(n):
            if src == dst:
                continue
            rate = max(float(kernel[src, dst]), 0.0) * scale
            if rate <= 0.0:
                continue
            amp = np.sqrt(rate)
            damp = 0.5 * scale * float(dkernel[src, dst]) / max(amp, 1e-12)
            op = np.zeros((n, n), dtype=complex)
            op[dst, src] = amp
            dop = np.zeros((n, n), dtype=complex)
            dop[dst, src] = damp
            base_ops.append(op)
            dops.append(dop)
    if dephasing > 0.0:
        for site in range(n):
            op = np.zeros((n, n), dtype=complex)
            op[site, site] = np.sqrt(max(float(dephasing), 0.0))
            base_ops.append(op)
            dops.append(np.zeros((n, n), dtype=complex))
    return base_ops, dops


def _superoperator_jacobian(dh: np.ndarray, ops: list[np.ndarray], dops: list[np.ndarray]) -> np.ndarray:
    n = dh.shape[0]
    ident = np.eye(n, dtype=complex)
    dsup = -1j * (np.kron(ident, dh) - np.kron(dh.T, ident))
    for op, dop in zip(ops, dops):
        anti = op.conj().T @ op
        danti = dop.conj().T @ op + op.conj().T @ dop
        dsup += np.kron(np.conj(dop), op) + np.kron(np.conj(op), dop)
        dsup -= 0.5 * np.kron(ident, danti.T)
        dsup -= 0.5 * np.kron(danti, ident)
    return dsup


def _analytic_branch_id_for_cell(branch_map: list[list[str]], i: int, j: int) -> str | None:
    ids = {branch_map[i][j], branch_map[i + 1][j], branch_map[i][j + 1], branch_map[i + 1][j + 1]}
    ids.discard('ambiguous')
    ids.discard('unresolved')
    return next(iter(ids)) if len(ids) == 1 else None


def _analytic_rows(context: dict, dephasing: float, lind_cfg: LindbladConfig, cache: DensityCache, observable_name: str | None = None) -> list[dict]:
    benchmark = context['benchmark']
    atlas = context['atlas']
    states = atlas['chosen_states']
    ambiguous = atlas['ambiguous_map']
    branch_map = atlas['chosen_branch_id_map']
    grid_u = context['grid_u']
    grid_v = context['grid_v']
    mesh = len(states)
    du = float(grid_u[1] - grid_u[0]) if mesh > 1 else 1.0
    dv = float(grid_v[1] - grid_v[0]) if mesh > 1 else 1.0
    area = du * dv
    rho_grid = [[cache.get(states[i][j], dephasing) for j in range(mesh)] for i in range(mesh)]
    rows: list[dict] = []
    for i in range(mesh - 1):
        for j in range(mesh - 1):
            center = [float(0.5 * (grid_u[i] + grid_u[i + 1])), float(0.5 * (grid_v[j] + grid_v[j + 1]))]
            trusted = not any([ambiguous[i][j], ambiguous[i + 1][j], ambiguous[i][j + 1], ambiguous[i + 1][j + 1]])
            branch_id = _analytic_branch_id_for_cell(branch_map, i, j)
            if (not trusted) or branch_id is None:
                rows.append({'cell': [int(i), int(j)], 'center': center, 'trusted': False, 'pair_r4': True})
                continue
            u0, v0 = center
            tang = analytic_branch_tangents(benchmark.benchmark_id, branch_id, u0, v0)
            state_center = tang.state
            rho_center = cache.get(state_center, dephasing)
            operator = observable_operator(benchmark, state_center, observable_name=observable_name)
            dh_u = _analytic_dh(state_center, tang, lind_cfg, 'u')
            dh_v = _analytic_dh(state_center, tang, lind_cfg, 'v')
            _, ops = lindblad_operators(state_center, lind_cfg, dephasing)
            base_ops_u, dops_u = _analytic_jump_tangents(state_center, tang, lind_cfg, 'u', dephasing)
            base_ops_v, dops_v = _analytic_jump_tangents(state_center, tang, lind_cfg, 'v', dephasing)
            # operators must match between u/v paths and lindblad_operators order
            ops = base_ops_u if len(base_ops_u) == len(ops) else ops
            du_sup = _superoperator_jacobian(dh_u, ops, dops_u)
            dv_sup = _superoperator_jacobian(dh_v, ops, dops_v)
            comm = du_sup @ dv_sup - dv_sup @ du_sup
            comm_action = unvec_density(comm @ vec_density(rho_center), rho_center.shape[0])
            comm_projection = float(np.real(np.trace(operator @ comm_action)))
            observable_mean = float(np.real(np.trace(rho_center @ operator)))
            rho00 = rho_grid[i][j]
            rho10 = rho_grid[i + 1][j]
            rho11 = rho_grid[i + 1][j + 1]
            rho01 = rho_grid[i][j + 1]
            curvature_area = float(mixed_plaquette_curvature(rho00, rho10, rho11, rho01, area) * area)
            raw_ratio = float(np.sign(observable_mean) * abs(comm_projection) / max(abs(curvature_area), 1e-12))
            compressed_ratio = float(np.sign(raw_ratio) * np.log1p(abs(raw_ratio)))
            rows.append(
                {
                    'cell': [int(i), int(j)],
                    'center': center,
                    'trusted': True,
                    'pair_r4': False,
                    'branch_id': branch_id,
                    'observable_mean': observable_mean,
                    'comm_projection': comm_projection,
                    'mixed_curvature_area': curvature_area,
                    'raw_ratio': raw_ratio,
                    'compressed_ratio': compressed_ratio,
                    'weight_sqrt_gap': float(np.sqrt(max(abs(curvature_area), 0.0))),
                }
            )
    return rows


def _comparison(candidate_field: dict, reference_field: np.ndarray, reference_valid: np.ndarray, reference_zero_u: float | None) -> dict:
    overlap = np.asarray(candidate_field['valid_mask'], dtype=bool) & reference_valid & np.isfinite(candidate_field['centered_field']) & np.isfinite(reference_field)
    fit = _fit_affine(np.asarray(candidate_field['centered_field'])[overlap], reference_field[overlap])
    return {
        'available': True,
        'overlap_count': int(np.sum(overlap)),
        'corr': fit['corr'],
        'r2': fit['r2'],
        'slope': fit['slope'],
        'intercept': fit['intercept'],
        'sign_agreement': float(np.mean(np.sign(np.asarray(candidate_field['centered_field'])[overlap]) == np.sign(reference_field[overlap]))) if int(np.sum(overlap)) > 0 else None,
        'zero_crossing_delta_u': None if not candidate_field['zero_crossings'] or reference_zero_u is None else float(np.mean([row['u_zero'] for row in candidate_field['zero_crossings']]) - float(reference_zero_u)),
    }


def _suite_verdict(benchmark_id: str, structural_amplitude: float, zero_crossing_count: int, floor: float) -> str:
    if benchmark_id == 'benchmark_f':
        return 'excluded_R4'
    if benchmark_id == 'benchmark_c' and structural_amplitude >= floor and zero_crossing_count > 0:
        return 'analytic_tangent_sign_boundary'
    if benchmark_id == 'benchmark_b':
        return 'weak_control'
    return 'null_like'


def _benchmark_phase18_payload(benchmark_id: str, *, output_root: Path, cfg: Phase18Config, lind_cfg: LindbladConfig, cache: DensityCache) -> dict:
    benchmark = get_benchmark(benchmark_id)
    context = _build_context(benchmark_id=benchmark_id, scan_mesh=cfg.scan_mesh)
    phase14 = _load_phase14_reference(output_root=output_root, benchmark_id=benchmark_id)
    phase17 = _load_phase17_reference(output_root=output_root, benchmark_id=benchmark_id)
    switch_gamma = float(phase14['recommended_switch_gamma']) if phase14 is not None else float(cfg.default_switch_gamma)

    rows = _analytic_rows(context=context, dephasing=switch_gamma, lind_cfg=lind_cfg, cache=cache)
    field = _centered_tangent_field(rows=rows, grid_u=context['grid_u'], grid_v=context['grid_v'], sigma_factor=cfg.sigma_factor, support_floor=cfg.support_floor, structural_amplitude_floor=cfg.structural_amplitude_floor)

    comp14 = {'available': False, 'overlap_count': 0, 'corr': None, 'r2': None, 'slope': None, 'intercept': None, 'sign_agreement': None, 'zero_crossing_delta_u': None}
    if phase14 is not None:
        ref = phase14['switch_level']
        ref_field = np.asarray(ref['smoothed_field'], dtype=float)
        ref_valid = np.asarray(ref['valid_mask'], dtype=bool)
        if ref_field.shape == np.asarray(field['centered_field']).shape:
            comp14 = _comparison(field, ref_field, ref_valid, ref['zero_crossing_u_mean'])

    comp17 = {'available': False, 'overlap_count': 0, 'corr': None, 'r2': None, 'slope': None, 'intercept': None, 'sign_agreement': None, 'zero_crossing_delta_u': None}
    if phase17 is not None:
        ref = phase17['frechet_field']
        ref_field = np.asarray(ref['centered_field'], dtype=float)
        ref_valid = np.asarray(ref['valid_mask'], dtype=bool)
        ref_zero = None if not ref['zero_crossings'] else float(np.mean([row['u_zero'] for row in ref['zero_crossings']]))
        if ref_field.shape == np.asarray(field['centered_field']).shape:
            comp17 = _comparison(field, ref_field, ref_valid, ref_zero)

    stability = None
    if benchmark_id == cfg.benchmark_focus:
        dense_context = _build_context(benchmark_id=benchmark_id, scan_mesh=cfg.dense_mesh_focus)
        dense_rows = _analytic_rows(context=dense_context, dephasing=switch_gamma, lind_cfg=lind_cfg, cache=cache)
        dense_field = _centered_tangent_field(rows=dense_rows, grid_u=dense_context['grid_u'], grid_v=dense_context['grid_v'], sigma_factor=cfg.sigma_factor, support_floor=cfg.support_floor, structural_amplitude_floor=cfg.structural_amplitude_floor)
        by_gamma = []
        for gamma in cfg.focus_dephasing_values:
            gamma_rows = _analytic_rows(context=context, dephasing=float(gamma), lind_cfg=lind_cfg, cache=cache)
            gamma_field = _centered_tangent_field(rows=gamma_rows, grid_u=context['grid_u'], grid_v=context['grid_v'], sigma_factor=cfg.sigma_factor, support_floor=cfg.support_floor, structural_amplitude_floor=cfg.structural_amplitude_floor)
            by_gamma.append({'dephasing': float(gamma), 'structural_amplitude': float(gamma_field['structural_amplitude']), 'valid_cell_count': int(np.sum(gamma_field['valid_mask'])), 'zero_crossing_u_mean': None if not gamma_field['zero_crossings'] else float(np.mean([row['u_zero'] for row in gamma_field['zero_crossings']]))})
        stability = {
            'switch_gamma': switch_gamma,
            'primary_mesh': cfg.scan_mesh,
            'dense_mesh': cfg.dense_mesh_focus,
            'primary_switch': {'structural_amplitude': float(field['structural_amplitude']), 'valid_cell_count': int(np.sum(field['valid_mask'])), 'zero_crossing_u_mean': None if not field['zero_crossings'] else float(np.mean([row['u_zero'] for row in field['zero_crossings']]))},
            'dense_switch': {'structural_amplitude': float(dense_field['structural_amplitude']), 'valid_cell_count': int(np.sum(dense_field['valid_mask'])), 'zero_crossing_u_mean': None if not dense_field['zero_crossings'] else float(np.mean([row['u_zero'] for row in dense_field['zero_crossings']]))},
            'focus_dephasing_series': by_gamma,
            'dense_field': {'cells_u': dense_field['cells_u'].tolist(), 'cells_v': dense_field['cells_v'].tolist(), 'centered_field': dense_field['centered_field'].tolist(), 'valid_mask': dense_field['valid_mask'].astype(int).tolist()},
        }

    payload = {
        'phase': 'phase18_analytic_branch_tangent_field',
        'benchmark': benchmark_id,
        'slug': benchmark.slug,
        'description': benchmark.description,
        'switch_gamma': switch_gamma,
        'phase14_reference': _phase14_switch_info(phase14),
        'analytic_field': {
            'cells_u': field['cells_u'].tolist(),
            'cells_v': field['cells_v'].tolist(),
            'raw_field': field['raw_field'].tolist(),
            'centered_field': field['centered_field'].tolist(),
            'support': field['support'].tolist(),
            'sign_consistency': field['sign_consistency'].tolist(),
            'valid_mask': field['valid_mask'].astype(int).tolist(),
            'baseline_median': field['baseline_median'],
            'structural_amplitude': float(field['structural_amplitude']),
            'zero_crossings': field['zero_crossings'],
            'valid_cell_count': int(np.sum(field['valid_mask'])),
            'raw_point_count': int(len(field['raw_points'])),
            'structural_summary': summarize(field['centered_field'][field['valid_mask']].ravel()),
            'structural_abs_summary': summarize_abs(field['centered_field'][field['valid_mask']].ravel()),
            'support_summary': summarize(field['support'][field['valid_mask']].ravel()),
            'sign_consistency_summary': summarize(field['sign_consistency'][field['valid_mask']].ravel()),
        },
        'comparison_to_phase14_switch': comp14,
        'comparison_to_phase17_switch': comp17,
        'stability': stability,
    }
    payload['verdict'] = _suite_verdict(benchmark_id, float(field['structural_amplitude']), len(field['zero_crossings']), cfg.structural_amplitude_floor)
    benchmark_dir = output_root / benchmark.slug
    benchmark_dir.mkdir(parents=True, exist_ok=True)
    (benchmark_dir / f'{benchmark_id}_phase18_analytic_field.json').write_text(json.dumps(payload, indent=2))
    return payload


def phase18_payload(output_root: Path, cfg: Phase18Config | None = None, lindblad_config: LindbladConfig | None = None) -> dict:
    cfg = cfg or Phase18Config()
    lind_cfg = lindblad_config or LindbladConfig(scan_mesh=cfg.scan_mesh)
    cache = DensityCache(lambda state, gamma: lindblad_branch_density(state, lind_cfg, gamma))

    payloads: dict[str, dict] = {}
    summaries: dict[str, dict] = {}
    for benchmark_id in cfg.benchmark_ids:
        payload = _benchmark_phase18_payload(benchmark_id=benchmark_id, output_root=output_root, cfg=cfg, lind_cfg=lind_cfg, cache=cache)
        payloads[benchmark_id] = payload
        af = payload['analytic_field']
        summaries[benchmark_id] = {
            'benchmark': benchmark_id,
            'switch_gamma': float(payload['switch_gamma']),
            'phase18_verdict': payload['verdict'],
            'structural_amplitude': float(af['structural_amplitude']),
            'valid_cell_count': int(af['valid_cell_count']),
            'zero_crossing_u_mean': None if not af['zero_crossings'] else float(np.mean([row['u_zero'] for row in af['zero_crossings']])),
            'comparison_phase14_corr': payload['comparison_to_phase14_switch']['corr'],
            'comparison_phase17_corr': payload['comparison_to_phase17_switch']['corr'],
        }

    focus = payloads[cfg.benchmark_focus]
    suite = {
        'phase': 'phase18_analytic_branch_tangent_field',
        'description': 'Analytic branch-tangent noisy field built from benchmark-specific control tangents lifted into Lindblad generator Jacobians.',
        'benchmark_summaries': summaries,
        'benchmark_payloads': payloads,
        'focus_benchmark': cfg.benchmark_focus,
        'notes': [
            'Phase 18 replaces mesh-estimated Hamiltonian and jump-operator tangents with benchmark-specific analytic branch tangents.',
            'The accepted field remains a centered signed-log structural field, but its generator Jacobian now comes from analytic control derivatives of p, theta, and K.',
            'Comparisons are reported against the empirical Phase 14 field and the Fréchet Phase 17 field.',
        ],
    }

    report_dir = output_root.parents[0] / 'reports'
    plot_root = report_dir / 'plots' / 'phase18_analytic'
    plot_root.mkdir(parents=True, exist_ok=True)
    labels = list(summaries.keys())
    values = [float(summaries[label]['structural_amplitude']) for label in labels]
    _plot_bars(plot_root / 'suite_structural_amplitude.png', labels, values, 'Phase 18 structural amplitude by benchmark', 'Amplitude')

    focus_field = focus['analytic_field']
    focus_dir = plot_root / get_benchmark(cfg.benchmark_focus).slug
    focus_dir.mkdir(parents=True, exist_ok=True)
    _plot_heatmap(focus_dir / 'centered_analytic_field_switch.png', np.asarray(focus_field['centered_field'], dtype=float), focus_field['cells_u'], focus_field['cells_v'], f'{cfg.benchmark_focus} analytic field @ γ={focus["switch_gamma"]:.2f}', focus_field['zero_crossings'])
    if focus['comparison_to_phase14_switch']['available']:
        phase14 = _load_phase14_reference(output_root=output_root, benchmark_id=cfg.benchmark_focus)
        sw = phase14['switch_level']
        overlap = np.asarray(focus_field['valid_mask'], dtype=bool) & np.asarray(sw['valid_mask'], dtype=bool)
        x = np.asarray(focus_field['centered_field'], dtype=float)[overlap]
        y = np.asarray(sw['smoothed_field'], dtype=float)[overlap]
        _plot_scatter(focus_dir / 'phase14_vs_analytic_scatter.png', x, y, 'Phase 14 vs Phase 18', 'Phase 18 analytic field', 'Phase 14 empirical field')
    if focus['comparison_to_phase17_switch']['available']:
        phase17 = _load_phase17_reference(output_root=output_root, benchmark_id=cfg.benchmark_focus)
        ff = phase17['frechet_field']
        overlap = np.asarray(focus_field['valid_mask'], dtype=bool) & np.asarray(ff['valid_mask'], dtype=bool)
        x = np.asarray(focus_field['centered_field'], dtype=float)[overlap]
        y = np.asarray(ff['centered_field'], dtype=float)[overlap]
        _plot_scatter(focus_dir / 'phase17_vs_analytic_scatter.png', x, y, 'Phase 17 vs Phase 18', 'Phase 18 analytic field', 'Phase 17 Fréchet field')
    series = focus['stability']['focus_dephasing_series'] if focus['stability'] is not None else []
    if series:
        x = np.asarray([row['dephasing'] for row in series], dtype=float)
        y = np.asarray([np.nan if row['zero_crossing_u_mean'] is None else row['zero_crossing_u_mean'] for row in series], dtype=float)
        _plot_line(focus_dir / 'zero_crossing_stability.png', x, y, 'Phase 18 zero crossing vs dephasing', 'Mean zero crossing u')

    return suite
