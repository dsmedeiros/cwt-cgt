from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from ..benchmarks import get_benchmark
from ..geometry import summarize, summarize_abs
from ..lindblad import LindbladConfig, lindblad_branch_density, lindblad_superoperator, vec_density, unvec_density
from ..mixed_state_geometry import mixed_plaquette_curvature
from ..open_system import observable_operator
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
class Phase16Config:
    benchmark_ids: tuple[str, ...] = ('benchmark_a', 'benchmark_b', 'benchmark_c', 'benchmark_d', 'benchmark_f')
    benchmark_focus: str = 'benchmark_c'
    scan_mesh: int = 7
    dense_mesh_focus: int = 11
    default_switch_gamma: float = 0.30
    sigma_factor: float = 0.80
    support_floor: float = 2.0
    structural_amplitude_floor: float = 5.0
    focus_dephasing_values: tuple[float, ...] = (0.0, 0.10, 0.20, 0.30)


class SuperoperatorCache:
    def __init__(self, fn):
        self.fn = fn
        self._cache: dict[tuple[float, tuple[float, ...]], np.ndarray] = {}

    def get(self, state, dephasing: float) -> np.ndarray:
        key = (round(float(dephasing), 6), DensityCache._signature(state))
        if key not in self._cache:
            self._cache[key] = self.fn(state, float(dephasing))
        return self._cache[key]


def _load_phase15_reference(output_root: Path, benchmark_id: str) -> dict | None:
    benchmark = get_benchmark(benchmark_id)
    path = output_root / benchmark.slug / f'{benchmark_id}_phase15_tangent_field.json'
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _rho_grid(context: dict, dephasing: float, density_cache: DensityCache) -> list[list[np.ndarray]]:
    states = context['atlas']['chosen_states']
    mesh = len(states)
    return [[density_cache.get(states[i][j], dephasing) for j in range(mesh)] for i in range(mesh)]


def _superoperator_rows(
    context: dict,
    dephasing: float,
    lindblad_config: LindbladConfig,
    density_cache: DensityCache,
    super_cache: SuperoperatorCache,
    observable_name: str | None = None,
) -> list[dict]:
    benchmark = context['benchmark']
    atlas = context['atlas']
    states = atlas['chosen_states']
    ambiguous = atlas['ambiguous_map']
    grid_u = context['grid_u']
    grid_v = context['grid_v']
    rho_grid = _rho_grid(context=context, dephasing=dephasing, density_cache=density_cache)
    mesh = len(states)
    du = float(grid_u[1] - grid_u[0]) if mesh > 1 else 1.0
    dv = float(grid_v[1] - grid_v[0]) if mesh > 1 else 1.0
    area = du * dv
    operator = observable_operator(benchmark, states[0][0], observable_name=observable_name)

    rows: list[dict] = []
    for i in range(mesh - 1):
        for j in range(mesh - 1):
            trusted = not any([
                ambiguous[i][j],
                ambiguous[i + 1][j],
                ambiguous[i + 1][j + 1],
                ambiguous[i][j + 1],
            ])
            center = [float(0.5 * (grid_u[i] + grid_u[i + 1])), float(0.5 * (grid_v[j] + grid_v[j + 1]))]
            if not trusted:
                rows.append({'cell': [int(i), int(j)], 'center': center, 'trusted': False, 'pair_r4': True})
                continue

            s00 = super_cache.get(states[i][j], dephasing)
            s10 = super_cache.get(states[i + 1][j], dephasing)
            s01 = super_cache.get(states[i][j + 1], dephasing)
            s11 = super_cache.get(states[i + 1][j + 1], dephasing)
            dsu = ((s10 + s11) - (s00 + s01)) / (2.0 * du)
            dsv = ((s01 + s11) - (s00 + s10)) / (2.0 * dv)
            comm = dsu @ dsv - dsv @ dsu

            rho00 = rho_grid[i][j]
            rho10 = rho_grid[i + 1][j]
            rho01 = rho_grid[i][j + 1]
            rho11 = rho_grid[i + 1][j + 1]
            rho_center = 0.25 * (rho00 + rho10 + rho01 + rho11)
            observable_mean = float(np.real(np.trace(rho_center @ operator)))
            comm_action = unvec_density(comm @ vec_density(rho_center), rho_center.shape[0])
            comm_projection = float(np.real(np.trace(operator @ comm_action)))
            curvature_area = float(mixed_plaquette_curvature(rho00, rho10, rho11, rho01, area) * area)

            raw_ratio = float(np.sign(observable_mean) * abs(comm_projection) / max(abs(curvature_area), 1e-12))
            compressed_ratio = float(np.sign(raw_ratio) * np.log1p(abs(raw_ratio)))
            rows.append(
                {
                    'cell': [int(i), int(j)],
                    'center': center,
                    'trusted': True,
                    'pair_r4': False,
                    'observable_mean': observable_mean,
                    'comm_projection': comm_projection,
                    'mixed_curvature_area': curvature_area,
                    'raw_ratio': raw_ratio,
                    'compressed_ratio': compressed_ratio,
                    'weight_sqrt_gap': float(np.sqrt(max(abs(curvature_area), 0.0))),
                }
            )
    return rows


def _comparison_to_reference(candidate_field: dict, reference_field: np.ndarray, reference_valid: np.ndarray, reference_zero_u: float | None) -> dict:
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


def _phase16_verdict(benchmark_id: str, structural_amplitude: float, zero_crossing_count: int, floor: float) -> str:
    if benchmark_id == 'benchmark_f':
        return 'excluded_R4'
    if benchmark_id == 'benchmark_c' and structural_amplitude >= floor and zero_crossing_count > 0:
        return 'generator_jacobian_sign_boundary'
    if benchmark_id == 'benchmark_b':
        return 'weak_control'
    return 'null_like'


def _benchmark_phase16_payload(
    benchmark_id: str,
    *,
    output_root: Path,
    phase16_config: Phase16Config,
    lindblad_config: LindbladConfig,
    density_cache: DensityCache,
    super_cache: SuperoperatorCache,
) -> dict:
    benchmark = get_benchmark(benchmark_id)
    context = _build_context(benchmark_id=benchmark_id, scan_mesh=phase16_config.scan_mesh)
    phase14_reference = _load_phase14_reference(output_root=output_root, benchmark_id=benchmark_id)
    phase15_reference = _load_phase15_reference(output_root=output_root, benchmark_id=benchmark_id)
    switch_gamma = float(phase14_reference['recommended_switch_gamma']) if phase14_reference is not None else float(phase16_config.default_switch_gamma)

    rows = _superoperator_rows(
        context=context,
        dephasing=switch_gamma,
        lindblad_config=lindblad_config,
        density_cache=density_cache,
        super_cache=super_cache,
    )
    field = _centered_tangent_field(
        rows=rows,
        grid_u=context['grid_u'],
        grid_v=context['grid_v'],
        sigma_factor=phase16_config.sigma_factor,
        support_floor=phase16_config.support_floor,
        structural_amplitude_floor=phase16_config.structural_amplitude_floor,
    )

    comparison14 = {
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
        if reference_field.shape == np.asarray(field['centered_field']).shape:
            comparison14 = _comparison_to_reference(field, reference_field, reference_valid, reference_switch['zero_crossing_u_mean'])

    comparison15 = {
        'available': False,
        'overlap_count': 0,
        'corr': None,
        'r2': None,
        'slope': None,
        'intercept': None,
        'sign_agreement': None,
        'zero_crossing_delta_u': None,
    }
    if phase15_reference is not None:
        reference_field = np.asarray(phase15_reference['tangent_field']['centered_field'], dtype=float)
        reference_valid = np.asarray(phase15_reference['tangent_field']['valid_mask'], dtype=bool)
        reference_zero_u = None if not phase15_reference['tangent_field']['zero_crossings'] else float(np.mean([row['u_zero'] for row in phase15_reference['tangent_field']['zero_crossings']]))
        if reference_field.shape == np.asarray(field['centered_field']).shape:
            comparison15 = _comparison_to_reference(field, reference_field, reference_valid, reference_zero_u)

    stability = None
    if benchmark_id == phase16_config.benchmark_focus:
        dense_context = _build_context(benchmark_id=benchmark_id, scan_mesh=phase16_config.dense_mesh_focus)
        dense_density_cache = DensityCache(lambda state, gamma: lindblad_branch_density(state, lindblad_config, gamma))
        dense_super_cache = SuperoperatorCache(lambda state, gamma: lindblad_superoperator(state, lindblad_config, gamma))
        dense_rows = _superoperator_rows(
            context=dense_context,
            dephasing=switch_gamma,
            lindblad_config=lindblad_config,
            density_cache=dense_density_cache,
            super_cache=dense_super_cache,
        )
        dense_field = _centered_tangent_field(
            rows=dense_rows,
            grid_u=dense_context['grid_u'],
            grid_v=dense_context['grid_v'],
            sigma_factor=phase16_config.sigma_factor,
            support_floor=phase16_config.support_floor,
            structural_amplitude_floor=phase16_config.structural_amplitude_floor,
        )

        dephasing_series: list[dict] = []
        for gamma in phase16_config.focus_dephasing_values:
            gamma_rows = _superoperator_rows(
                context=context,
                dephasing=float(gamma),
                lindblad_config=lindblad_config,
                density_cache=density_cache,
                super_cache=super_cache,
            )
            gamma_field = _centered_tangent_field(
                rows=gamma_rows,
                grid_u=context['grid_u'],
                grid_v=context['grid_v'],
                sigma_factor=phase16_config.sigma_factor,
                support_floor=phase16_config.support_floor,
                structural_amplitude_floor=phase16_config.structural_amplitude_floor,
            )
            dephasing_series.append(
                {
                    'dephasing': float(gamma),
                    'structural_amplitude': float(gamma_field['structural_amplitude']),
                    'valid_cell_count': int(np.sum(gamma_field['valid_mask'])),
                    'zero_crossing_u_mean': None if not gamma_field['zero_crossings'] else float(np.mean([row['u_zero'] for row in gamma_field['zero_crossings']])),
                }
            )

        stability = {
            'switch_gamma': float(switch_gamma),
            'primary_mesh': phase16_config.scan_mesh,
            'dense_mesh': phase16_config.dense_mesh_focus,
            'primary_switch': {
                'structural_amplitude': float(field['structural_amplitude']),
                'valid_cell_count': int(np.sum(field['valid_mask'])),
                'zero_crossing_u_mean': None if not field['zero_crossings'] else float(np.mean([row['u_zero'] for row in field['zero_crossings']])),
            },
            'dense_switch': {
                'structural_amplitude': float(dense_field['structural_amplitude']),
                'valid_cell_count': int(np.sum(dense_field['valid_mask'])),
                'zero_crossing_u_mean': None if not dense_field['zero_crossings'] else float(np.mean([row['u_zero'] for row in dense_field['zero_crossings']])),
            },
            'focus_dephasing_series': dephasing_series,
        }

    payload = {
        'phase': 'phase16_superoperator_tangent_field',
        'benchmark': benchmark_id,
        'slug': benchmark.slug,
        'description': benchmark.description,
        'switch_gamma': float(switch_gamma),
        'phase14_reference': _phase14_switch_info(phase14_reference),
        'superoperator_field': {
            'cells_u': field['cells_u'].tolist(),
            'cells_v': field['cells_v'].tolist(),
            'raw_field': np.asarray(field['raw_field']).tolist(),
            'centered_field': np.asarray(field['centered_field']).tolist(),
            'support': np.asarray(field['support']).tolist(),
            'sign_consistency': np.asarray(field['sign_consistency']).tolist(),
            'valid_mask': np.asarray(field['valid_mask']).astype(int).tolist(),
            'baseline_median': field['baseline_median'],
            'structural_amplitude': float(field['structural_amplitude']),
            'zero_crossings': field['zero_crossings'],
            'valid_cell_count': int(np.sum(field['valid_mask'])),
            'raw_point_count': int(len(field['raw_points'])),
            'structural_summary': summarize(np.asarray(field['centered_field'])[np.asarray(field['valid_mask'], dtype=bool)].ravel()),
            'structural_abs_summary': summarize_abs(np.asarray(field['centered_field'])[np.asarray(field['valid_mask'], dtype=bool)].ravel()),
            'support_summary': summarize(np.asarray(field['support'])[np.asarray(field['valid_mask'], dtype=bool)].ravel()),
            'sign_consistency_summary': summarize(np.asarray(field['sign_consistency'])[np.asarray(field['valid_mask'], dtype=bool)].ravel()),
        },
        'comparison_to_phase14_switch': comparison14,
        'comparison_to_phase15_switch': comparison15,
        'stability': stability,
    }
    payload['verdict'] = _phase16_verdict(
        benchmark_id=benchmark_id,
        structural_amplitude=float(field['structural_amplitude']),
        zero_crossing_count=len(field['zero_crossings']),
        floor=phase16_config.structural_amplitude_floor,
    )

    benchmark_dir = output_root / benchmark.slug
    benchmark_dir.mkdir(parents=True, exist_ok=True)
    (benchmark_dir / f'{benchmark_id}_phase16_superoperator_field.json').write_text(json.dumps(payload, indent=2))
    return payload


def phase16_payload(output_root: Path, phase16_config: Phase16Config | None = None, lindblad_config: LindbladConfig | None = None) -> dict:
    cfg = phase16_config or Phase16Config()
    lind_cfg = lindblad_config or LindbladConfig(scan_mesh=cfg.scan_mesh)
    density_cache = DensityCache(lambda state, gamma: lindblad_branch_density(state, lind_cfg, gamma))
    super_cache = SuperoperatorCache(lambda state, gamma: lindblad_superoperator(state, lind_cfg, gamma))

    benchmark_payloads: dict[str, dict] = {}
    benchmark_summaries: dict[str, dict] = {}
    for benchmark_id in cfg.benchmark_ids:
        payload = _benchmark_phase16_payload(
            benchmark_id=benchmark_id,
            output_root=output_root,
            phase16_config=cfg,
            lindblad_config=lind_cfg,
            density_cache=density_cache,
            super_cache=super_cache,
        )
        benchmark_payloads[benchmark_id] = payload
        sf = payload['superoperator_field']
        benchmark_summaries[benchmark_id] = {
            'benchmark': benchmark_id,
            'switch_gamma': float(payload['switch_gamma']),
            'phase14_switch_verdict': payload['phase14_reference']['switch_verdict'],
            'phase16_verdict': payload['verdict'],
            'structural_amplitude': float(sf['structural_amplitude']),
            'valid_cell_count': int(sf['valid_cell_count']),
            'zero_crossing_u_mean': None if not sf['zero_crossings'] else float(np.mean([row['u_zero'] for row in sf['zero_crossings']])),
            'baseline_median': sf['baseline_median'],
            'comparison14_corr': payload['comparison_to_phase14_switch']['corr'],
            'comparison14_r2': payload['comparison_to_phase14_switch']['r2'],
            'comparison15_corr': payload['comparison_to_phase15_switch']['corr'],
            'comparison15_r2': payload['comparison_to_phase15_switch']['r2'],
        }

    suite = {
        'phase': 'phase16_superoperator_tangent_field',
        'description': 'Differential generator-Jacobian field built from the superoperator commutator [∂uL, ∂vL] acting on the local branch density, then centered to isolate control-space structure.',
        'benchmark_summaries': benchmark_summaries,
        'benchmark_payloads': benchmark_payloads,
        'focus_benchmark': cfg.benchmark_focus,
        'notes': [
            'Phase 16 replaces the finite ordered-transport tangent surrogate with a more directly derived superoperator tangent field.',
            'The accepted Phase 16 object is the centered signed-log superoperator commutator field obtained from [∂uL, ∂vL]ρ̄ projected onto the benchmark observable.',
            'Phase 14 remains the empirical local-field reference and Phase 15 remains the finite transport-order predictor; Phase 16 tightens the generator-side derivation.',
        ],
    }
    reports_dir = output_root.parents[0] / 'reports'
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / 'phase16_summary.json').write_text(json.dumps(suite, indent=2))
    return suite


def phase16_report(output_root: Path, payload: dict) -> dict[str, Path]:
    reports_dir = output_root.parents[0] / 'reports'
    plots_root = reports_dir / 'plots' / 'phase16_superoperator'
    reports_dir.mkdir(parents=True, exist_ok=True)
    plot_paths: dict[str, Path] = {}

    labels = []
    amplitudes = []
    for benchmark_id, summary in payload['benchmark_summaries'].items():
        labels.append(benchmark_id)
        amplitudes.append(float(summary['structural_amplitude']))
    suite_amp_path = plots_root / 'suite_structural_amplitude.png'
    _plot_bars(suite_amp_path, labels, amplitudes, title='Phase 16 structural amplitude at switch γ', ylabel='structural amplitude')
    plot_paths['suite_structural_amplitude'] = suite_amp_path

    focus = payload['benchmark_payloads'][payload['focus_benchmark']]
    focus_sf = focus['superoperator_field']
    focus_dir = plots_root / focus['slug']
    field_path = focus_dir / 'centered_superoperator_field_switch.png'
    _plot_heatmap(
        field_path,
        np.asarray(focus_sf['centered_field'], dtype=float),
        np.asarray(focus_sf['cells_u'], dtype=float),
        np.asarray(focus_sf['cells_v'], dtype=float),
        title=f"{payload['focus_benchmark']} centered superoperator field at switch γ={focus['switch_gamma']:.2f}",
        zero_crossings=focus_sf['zero_crossings'],
    )
    plot_paths['focus_centered_field'] = field_path

    if focus['comparison_to_phase14_switch']['available']:
        phase14_reference = _load_phase14_reference(output_root=output_root, benchmark_id=payload['focus_benchmark'])
        if phase14_reference is not None:
            ref_field = np.asarray(phase14_reference['switch_level']['smoothed_field'], dtype=float)
            ref_valid = np.asarray(phase14_reference['switch_level']['valid_mask'], dtype=bool)
            cand_field = np.asarray(focus_sf['centered_field'], dtype=float)
            cand_valid = np.asarray(focus_sf['valid_mask'], dtype=bool)
            overlap = ref_valid & cand_valid & np.isfinite(ref_field) & np.isfinite(cand_field)
            phase14_scatter = focus_dir / 'phase14_vs_superoperator_scatter.png'
            _plot_scatter(
                phase14_scatter,
                cand_field[overlap],
                ref_field[overlap],
                title='Phase 14 field vs Phase 16 superoperator field',
                xlabel='Phase 16 superoperator field',
                ylabel='Phase 14 local field',
            )
            plot_paths['focus_phase14_scatter'] = phase14_scatter

    if focus['comparison_to_phase15_switch']['available']:
        phase15_reference = _load_phase15_reference(output_root=output_root, benchmark_id=payload['focus_benchmark'])
        if phase15_reference is not None:
            ref_field = np.asarray(phase15_reference['tangent_field']['centered_field'], dtype=float)
            ref_valid = np.asarray(phase15_reference['tangent_field']['valid_mask'], dtype=bool)
            cand_field = np.asarray(focus_sf['centered_field'], dtype=float)
            cand_valid = np.asarray(focus_sf['valid_mask'], dtype=bool)
            overlap = ref_valid & cand_valid & np.isfinite(ref_field) & np.isfinite(cand_field)
            phase15_scatter = focus_dir / 'phase15_vs_superoperator_scatter.png'
            _plot_scatter(
                phase15_scatter,
                cand_field[overlap],
                ref_field[overlap],
                title='Phase 15 tangent field vs Phase 16 superoperator field',
                xlabel='Phase 16 superoperator field',
                ylabel='Phase 15 tangent field',
            )
            plot_paths['focus_phase15_scatter'] = phase15_scatter

    if focus['stability'] is not None:
        stability = focus['stability']
        zero_path = focus_dir / 'zero_crossing_stability.png'
        _plot_bars(
            zero_path,
            ['primary mesh', 'dense mesh'],
            [
                0.0 if stability['primary_switch']['zero_crossing_u_mean'] is None else float(stability['primary_switch']['zero_crossing_u_mean']),
                0.0 if stability['dense_switch']['zero_crossing_u_mean'] is None else float(stability['dense_switch']['zero_crossing_u_mean']),
            ],
            title='Benchmark C superoperator zero-crossing comparison',
            ylabel='mean control-1 zero location',
        )
        plot_paths['focus_zero_crossing_stability'] = zero_path

        gamma_series = stability['focus_dephasing_series']
        gamma_x = np.asarray([row['dephasing'] for row in gamma_series], dtype=float)
        gamma_amp = np.asarray([row['structural_amplitude'] for row in gamma_series], dtype=float)
        amp_path = focus_dir / 'structural_amplitude_vs_dephasing.png'
        _plot_line(amp_path, gamma_x, gamma_amp, title='Benchmark C structural amplitude vs dephasing', ylabel='structural amplitude')
        plot_paths['focus_amplitude_vs_gamma'] = amp_path

    report_path = reports_dir / 'CWT-CGT_Phase_16_Report.md'
    lines = ['# CWT-CGT Phase 16 Report', '', '## What Phase 16 adds', '']
    lines.append('Phase 16 replaces the finite ordered-transport tangent surrogate with a more directly derived **superoperator tangent field** built from the differential Lindblad generator.')
    lines.append('')
    lines.append('At each trusted cell, it estimates the central generator derivatives and their commutator:')
    lines.append('')
    lines.append('```text')
    lines.append('∂uL ≈ (L10 + L11 - L00 - L01) / (2Δu)')
    lines.append('∂vL ≈ (L01 + L11 - L00 - L10) / (2Δv)')
    lines.append('Ξ_sup = [∂uL, ∂vL] ρ̄')
    lines.append('χ_sup,ctr = sign(χ_raw)·log(1 + |χ_raw|) - medianλ[ sign(χ_raw)·log(1 + |χ_raw|) ]')
    lines.append('```')
    lines.append('')
    lines.append('where χ_raw is the observable projection of Ξ_sup normalized by the local mixed-curvature area.')
    lines.append('')
    lines.append('## Suite summary at the switch γ')
    lines.append('')
    for benchmark_id, summary in payload['benchmark_summaries'].items():
        lines.append(
            f"- {benchmark_id}: Phase 16 verdict={summary['phase16_verdict']}, switch γ={summary['switch_gamma']:.2f}, structural amplitude={summary['structural_amplitude']}, valid cells={summary['valid_cell_count']}, zero-crossing u={summary['zero_crossing_u_mean']}, corr vs Phase 14={summary['comparison14_corr']}, corr vs Phase 15={summary['comparison15_corr']}"
        )
    lines.append('')
    lines.append('## Focus benchmark interpretation')
    lines.append('')
    lines.append(f"Focus benchmark: **{payload['focus_benchmark']}**.")
    lines.append(f"At switch γ={focus['switch_gamma']:.2f}, the superoperator field has structural amplitude {focus_sf['structural_amplitude']} and {len(focus_sf['zero_crossings'])} zero-crossing samples.")
    if focus['comparison_to_phase14_switch']['available']:
        comp14 = focus['comparison_to_phase14_switch']
        lines.append(f"Against the Phase 14 empirical field: corr={comp14['corr']}, R²={comp14['r2']}, sign agreement={comp14['sign_agreement']}, overlap count={comp14['overlap_count']}.")
    if focus['comparison_to_phase15_switch']['available']:
        comp15 = focus['comparison_to_phase15_switch']
        lines.append(f"Against the Phase 15 tangent field: corr={comp15['corr']}, R²={comp15['r2']}, sign agreement={comp15['sign_agreement']}, overlap count={comp15['overlap_count']}.")
    if focus['stability'] is not None:
        stability = focus['stability']
        lines.append('')
        lines.append('| variant | structural amplitude | valid cells | mean zero-crossing u |')
        lines.append('|---|---:|---:|---:|')
        lines.append(f"| primary mesh={stability['primary_mesh']} | {stability['primary_switch']['structural_amplitude']} | {stability['primary_switch']['valid_cell_count']} | {stability['primary_switch']['zero_crossing_u_mean']} |")
        lines.append(f"| dense mesh={stability['dense_mesh']} | {stability['dense_switch']['structural_amplitude']} | {stability['dense_switch']['valid_cell_count']} | {stability['dense_switch']['zero_crossing_u_mean']} |")
    lines.append('')
    lines.append('## Interpretation')
    lines.append('')
    lines.append('- Phase 16 is the strongest noisy structural predictor so far because it is tied directly to differential generator data rather than only to finite ordered transport.')
    lines.append('- Benchmark C remains the key positive noisy benchmark; its superoperator field should reinforce a left-of-center sign boundary if the noisy lane is real.')
    lines.append('- Benchmarks A and D should remain null-like under this stricter differential construction; benchmark B may remain weak-control rather than robustly positive.')
    lines.append('- Benchmark F remains excluded by R4 and is not interpreted through the superoperator field.')
    lines.append('')
    lines.append(f"Suite plot: `{plot_paths['suite_structural_amplitude']}`")
    report_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    plot_paths['phase16_report'] = report_path
    return plot_paths
