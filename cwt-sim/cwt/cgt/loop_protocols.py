from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from ._geom_compat import (
    berry_loop_flux,
    overlap,
    phase_coherence,
    polygon_signed_area,
    psi_from_state,
    summarize_abs,
    wrap_phase,
)
from .benchmarks import get_benchmark
from .models import BenchmarkDefinition, LoopConfig


def _square_loop(center: tuple[float, float], side: float, orientation: str, steps_per_segment: int) -> list[tuple[float, float]]:
    u0, v0 = center
    half = side / 2.0
    corners = [(u0 - half, v0 - half), (u0 + half, v0 - half), (u0 + half, v0 + half), (u0 - half, v0 + half)]
    if orientation == 'cw':
        corners = [corners[0], corners[3], corners[2], corners[1]]
    path: list[tuple[float, float]] = []
    for idx in range(4):
        start = np.asarray(corners[idx], dtype=float)
        stop = np.asarray(corners[(idx + 1) % 4], dtype=float)
        for step in range(steps_per_segment):
            point = start + (stop - start) * (step / steps_per_segment)
            path.append((float(point[0]), float(point[1])))
    path.append(path[0])
    return path


def _circle_loop(center: tuple[float, float], side: float, orientation: str, steps_per_segment: int) -> list[tuple[float, float]]:
    radius = side / 2.0
    samples = max(16, 4 * steps_per_segment)
    sign = 1.0 if orientation == 'ccw' else -1.0
    path: list[tuple[float, float]] = []
    for idx in range(samples):
        angle = sign * 2.0 * np.pi * idx / samples
        u = center[0] + radius * math.cos(angle)
        v = center[1] + radius * math.sin(angle)
        path.append((float(u), float(v)))
    path.append(path[0])
    return path


def build_loop_path(
    center: tuple[float, float],
    side: float,
    orientation: str,
    shape: str,
    steps_per_segment: int,
) -> list[tuple[float, float]]:
    if shape == 'square':
        return _square_loop(center=center, side=side, orientation=orientation, steps_per_segment=steps_per_segment)
    if shape == 'circle':
        return _circle_loop(center=center, side=side, orientation=orientation, steps_per_segment=steps_per_segment)
    raise ValueError(f'Unsupported loop shape: {shape}')


def _circulation_current(p: np.ndarray, theta_actual: np.ndarray, theta_branch: np.ndarray, kernel: np.ndarray, phase_gain: float) -> tuple[float, float]:
    phase_factor_actual = 1.0 + phase_gain * np.sin(theta_actual[None, :] - theta_actual[:, None])
    phase_factor_branch = 1.0 + phase_gain * np.sin(theta_branch[None, :] - theta_branch[:, None])
    current_actual = p[:, None] * kernel * phase_factor_actual
    current_branch = p[:, None] * kernel * phase_factor_branch
    circ_actual = float((current_actual[0, 1] + current_actual[1, 2] + current_actual[2, 0]) - (current_actual[1, 0] + current_actual[2, 1] + current_actual[0, 2]))
    circ_branch = float((current_branch[0, 1] + current_branch[1, 2] + current_branch[2, 0]) - (current_branch[1, 0] + current_branch[2, 1] + current_branch[0, 2]))
    return circ_actual, circ_branch


def _secondary_value(benchmark: BenchmarkDefinition, final_state) -> float | None:
    if benchmark.secondary_observable == 'final_p1':
        return float(final_state.p[0])
    if benchmark.secondary_observable == 'final_p5':
        return float(final_state.p[4])
    return None


def _primary_value(
    benchmark: BenchmarkDefinition,
    final_state,
    raw_samples: list[float],
    branch_samples: list[float],
    use_excess_circulation: bool,
) -> tuple[float, float | None, float | None]:
    if benchmark.primary_observable == 'final_p1':
        value = float(final_state.p[0])
        return value, None, None
    if benchmark.primary_observable == 'final_p3':
        value = float(final_state.p[2])
        return value, None, None
    if benchmark.primary_observable == 'mean_position':
        indices = np.arange(1, final_state.p.size + 1, dtype=float)
        value = float(np.dot(indices, final_state.p))
        return value, None, None
    if benchmark.primary_observable == 'excess_circulation':
        raw = float(np.mean(raw_samples)) if raw_samples else 0.0
        branch = float(np.mean(branch_samples)) if branch_samples else 0.0
        value = raw - branch if use_excess_circulation else raw
        return value, raw, branch
    raise ValueError(f'Unsupported observable: {benchmark.primary_observable}')


def classify_loop_regime(avg_overlap: float, avg_coherence: float, max_adiabatic_proxy: float, config: LoopConfig) -> str:
    if avg_overlap < config.overlap_floor or avg_coherence < config.coherence_floor:
        return 'R3'
    if max_adiabatic_proxy > config.adiabatic_max:
        return 'R2'
    return 'R1'


def run_single_loop(
    benchmark: BenchmarkDefinition,
    center: tuple[float, float],
    side: float,
    orientation: str,
    config: LoopConfig,
) -> dict:
    path = build_loop_path(center=center, side=side, orientation=orientation, shape=config.shape, steps_per_segment=config.steps_per_segment)
    states = [benchmark.branch_state_fn(*point) for point in path]
    theta_actual = states[0].theta.copy()
    overlaps: list[float] = []
    coherences: list[float] = []
    adiabatic_proxy: list[float] = []
    raw_samples: list[float] = []
    branch_samples: list[float] = []
    last_psi = psi_from_state(states[0])

    for state in states:
        psi_branch = psi_from_state(state)
        overlaps.append(overlap(last_psi, psi_branch))
        coherences.append(phase_coherence(state))
        lag = np.asarray(wrap_phase(state.theta - theta_actual), dtype=float)
        adiabatic_proxy.append(float(np.linalg.norm(lag) / max(np.sqrt(state.theta.size), 1.0) / np.pi))
        theta_actual = np.asarray(wrap_phase(theta_actual + config.phase_relaxation * lag), dtype=float)

        if benchmark.primary_observable == 'excess_circulation':
            raw_value, branch_value = _circulation_current(
                p=state.p,
                theta_actual=theta_actual,
                theta_branch=state.theta,
                kernel=state.kernel,
                phase_gain=config.current_phase_gain,
            )
            raw_samples.append(raw_value)
            branch_samples.append(branch_value)
        last_psi = psi_branch

    final_state = states[-1]
    response, raw_response, branch_response = _primary_value(
        benchmark=benchmark,
        final_state=final_state,
        raw_samples=raw_samples,
        branch_samples=branch_samples,
        use_excess_circulation=config.use_excess_circulation,
    )
    secondary_value = _secondary_value(benchmark=benchmark, final_state=final_state)
    signed_area = polygon_signed_area(path)
    signed_flux = berry_loop_flux(states)
    avg_overlap = float(np.mean(overlaps)) if overlaps else math.nan
    avg_coherence = float(np.mean(coherences)) if coherences else math.nan
    max_adiabatic = float(np.max(adiabatic_proxy)) if adiabatic_proxy else math.nan
    regime = classify_loop_regime(avg_overlap=avg_overlap, avg_coherence=avg_coherence, max_adiabatic_proxy=max_adiabatic, config=config)
    bounds_u = [float(min(point[0] for point in path)), float(max(point[0] for point in path))]
    bounds_v = [float(min(point[1] for point in path)), float(max(point[1] for point in path))]
    return {
        'center': [float(center[0]), float(center[1])],
        'shape': config.shape,
        'side_length': float(side),
        'orientation': orientation,
        'signed_area': float(signed_area),
        'signed_flux': float(signed_flux),
        'response': float(response),
        'raw_response': None if raw_response is None else float(raw_response),
        'branch_response': None if branch_response is None else float(branch_response),
        'secondary_value': secondary_value,
        'avg_overlap': avg_overlap,
        'avg_coherence': avg_coherence,
        'max_adiabatic_proxy': max_adiabatic,
        'regime_label': regime,
        'trusted_r1': regime == 'R1',
        'path_bounds': {
            'u': bounds_u,
            'v': bounds_v,
        },
        'path_length': int(len(path)),
    }


def _pair_summary(benchmark: BenchmarkDefinition, ccw: dict, cw: dict) -> dict:
    tol = 1e-8
    def _sign(value: float) -> int:
        if value > tol:
            return 1
        if value < -tol:
            return -1
        return 0

    sign_flip = _sign(ccw['response']) == -_sign(cw['response']) and (_sign(ccw['response']) != 0 or _sign(cw['response']) != 0)
    return {
        'center': ccw['center'],
        'shape': ccw['shape'],
        'side_length': ccw['side_length'],
        'area_magnitude': abs(ccw['signed_area']),
        'flux_magnitude': abs(ccw['signed_flux']),
        'pair_regime': ccw['regime_label'] if ccw['regime_label'] == cw['regime_label'] else f"mixed({ccw['regime_label']},{cw['regime_label']})",
        'pair_trusted_r1': bool(ccw['trusted_r1'] and cw['trusted_r1']),
        'flux_sign_reversed': _sign(ccw['signed_flux']) == -_sign(cw['signed_flux']) or (abs(ccw['signed_flux']) < tol and abs(cw['signed_flux']) < tol),
        'response_sign_reversed': sign_flip,
        'orientation_gap': float(ccw['response'] - cw['response']),
        'orientation_sum': float(ccw['response'] + cw['response']),
        'ccw': ccw,
        'cw': cw,
    }


def _fit_through_origin(xs: np.ndarray, ys: np.ndarray) -> dict[str, float | None]:
    if xs.size == 0 or np.allclose(xs, 0.0):
        return {'slope': None, 'r2': None, 'count': int(xs.size)}
    slope = float(np.dot(xs, ys) / np.dot(xs, xs))
    residual = ys - slope * xs
    denom = float(np.dot(ys, ys))
    r2 = None if denom <= 1e-15 else float(1.0 - np.dot(residual, residual) / denom)
    return {'slope': slope, 'r2': r2, 'count': int(xs.size)}


def run_benchmark_loops(benchmark_id: str, output_root: Path, config: LoopConfig | None = None) -> dict:
    benchmark = get_benchmark(benchmark_id)
    loop_config = config or LoopConfig()
    centers = loop_config.centers or benchmark.default_loop_centers
    side_lengths = loop_config.side_lengths or benchmark.default_loop_side_lengths
    comparisons: list[dict] = []
    flat_runs: list[dict] = []

    for center_index, center in enumerate(centers):
        for side in side_lengths:
            ccw = run_single_loop(benchmark=benchmark, center=center, side=side, orientation='ccw', config=loop_config)
            cw = run_single_loop(benchmark=benchmark, center=center, side=side, orientation='cw', config=loop_config)
            pair = _pair_summary(benchmark=benchmark, ccw=ccw, cw=cw)
            pair['center_index'] = center_index
            comparisons.append(pair)
            flat_runs.extend([ccw, cw])

    trusted_pairs = [pair for pair in comparisons if pair['pair_trusted_r1']]
    signed_areas: list[float] = []
    signed_fluxes: list[float] = []
    responses: list[float] = []
    for pair in trusted_pairs:
        signed_areas.extend([pair['ccw']['signed_area'], pair['cw']['signed_area']])
        signed_fluxes.extend([pair['ccw']['signed_flux'], pair['cw']['signed_flux']])
        responses.extend([pair['ccw']['response'], pair['cw']['response']])

    fit_vs_area = _fit_through_origin(np.asarray(signed_areas, dtype=float), np.asarray(responses, dtype=float))
    fit_vs_flux = _fit_through_origin(np.asarray(signed_fluxes, dtype=float), np.asarray(responses, dtype=float))
    sign_flip_fraction = float(np.mean([pair['response_sign_reversed'] for pair in trusted_pairs])) if trusted_pairs else 0.0
    summary = {
        'benchmark': benchmark.benchmark_id,
        'trusted_pair_count': int(len(trusted_pairs)),
        'pair_count': int(len(comparisons)),
        'sign_flip_fraction_r1': sign_flip_fraction,
        'flux_summary': summarize_abs(run['signed_flux'] for run in flat_runs),
        'response_summary': summarize_abs(run['response'] for run in flat_runs),
        'orientation_gap_summary': summarize_abs(pair['orientation_gap'] for pair in comparisons),
        'fit_response_vs_signed_area': fit_vs_area,
        'fit_response_vs_signed_flux': fit_vs_flux,
    }
    notes = []
    if benchmark.benchmark_id in {'benchmark_a', 'benchmark_b', 'benchmark_d'}:
        notes.append('Null/near-null benchmark: any strong reproducible signed loop law should be treated as a warning.')
    if benchmark.benchmark_id == 'benchmark_c' and loop_config.use_excess_circulation:
        notes.append('Response uses excess circulation (raw minus branch baseline) to separate path-induced pumping from static chirality bias.')

    payload = {
        'benchmark': benchmark.benchmark_id,
        'description': benchmark.description,
        'expected_behavior': benchmark.expected_behavior,
        'expected_regime': benchmark.expected_regime,
        'control_names': list(benchmark.control_names),
        'loop_family': {
            'shape': loop_config.shape,
            'centers': [list(center) for center in centers],
            'side_lengths': list(side_lengths),
            'steps_per_segment': loop_config.steps_per_segment,
            'phase_relaxation': loop_config.phase_relaxation,
            'current_phase_gain': loop_config.current_phase_gain,
            'use_excess_circulation': loop_config.use_excess_circulation,
        },
        'pair_results': comparisons,
        'summary': summary,
        'notes': notes,
    }

    benchmark_dir = output_root / benchmark.slug
    benchmark_dir.mkdir(parents=True, exist_ok=True)
    output_path = benchmark_dir / f'{benchmark.benchmark_id}_loops.json'
    output_path.write_text(__import__('json').dumps(payload, indent=2))
    return payload
