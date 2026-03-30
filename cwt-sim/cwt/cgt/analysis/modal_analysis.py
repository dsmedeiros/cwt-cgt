from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .._geom_compat import summarize, summarize_abs
from ..benchmarks import get_benchmark
from ..continuation import build_branch_atlas, continue_path_with_branch_ids
from ..loop_protocols import build_loop_path, run_benchmark_loops
from ..modal import (
    auxiliary_operator_from_state,
    biorthogonal_modal_frame,
    modal_diagnostics,
    mode_wilson_phase,
    off_diagonal_mixing_score,
)
from ..models import LoopConfig, ScanConfig
from ..robustness import protocol_suite, run_robustness_suite
from ..runner import run_benchmark_scan


def _grid(bounds: tuple[float, float], mesh: int) -> np.ndarray:
    return np.linspace(bounds[0], bounds[1], mesh, dtype=float)


def _fit_through_origin(xs: np.ndarray, ys: np.ndarray) -> dict[str, float | None]:
    if xs.size == 0 or np.allclose(xs, 0.0):
        return {'slope': None, 'r2': None, 'count': int(xs.size)}
    slope = float(np.dot(xs, ys) / np.dot(xs, xs))
    residual = ys - slope * xs
    denom = float(np.dot(ys, ys))
    r2 = None if denom <= 1e-15 else float(1.0 - np.dot(residual, residual) / denom)
    return {'slope': slope, 'r2': r2, 'count': int(xs.size)}


def _corr(xs: np.ndarray, ys: np.ndarray) -> float | None:
    mask = np.isfinite(xs) & np.isfinite(ys)
    if np.count_nonzero(mask) < 3:
        return None
    x = xs[mask]
    y = ys[mask]
    if np.allclose(x, x.mean()) or np.allclose(y, y.mean()):
        return None
    return float(np.corrcoef(x, y)[0, 1])


def modal_scan_payload(benchmark_id: str, output_root: Path, scan_config: ScanConfig | None = None) -> dict:
    scan_config = scan_config or ScanConfig()
    benchmark = get_benchmark(benchmark_id)
    scan_payload = run_benchmark_scan(benchmark_id, output_root=output_root, config=scan_config)
    grid_u = np.asarray(scan_payload['grid_u'], dtype=float)
    grid_v = np.asarray(scan_payload['grid_v'], dtype=float)
    atlas = build_branch_atlas(benchmark, grid_u, grid_v, scan_config)
    rows, cols = grid_u.size, grid_v.size

    gap_map = np.full((rows, cols), np.nan, dtype=float)
    inverse_gap_map = np.full((rows, cols), np.nan, dtype=float)
    biorthogonality_map = np.full((rows, cols), np.nan, dtype=float)
    dominant_phase_map = np.full((rows, cols), np.nan, dtype=float)
    frames = [[None for _ in range(cols)] for _ in range(rows)]

    for i in range(rows):
        for j in range(cols):
            if atlas['ambiguous_map'][i][j]:
                continue
            frame = biorthogonal_modal_frame(auxiliary_operator_from_state(atlas['chosen_states'][i][j]))
            diag = modal_diagnostics(frame)
            frames[i][j] = frame
            gap_map[i, j] = diag.spectral_gap
            inverse_gap_map[i, j] = diag.inverse_gap_proxy
            biorthogonality_map[i, j] = diag.biorthogonality_error
            dominant_phase_map[i, j] = diag.dominant_phase

    warning_tiles = []
    for i in range(rows):
        for j in range(cols):
            if np.isfinite(gap_map[i, j]) and (gap_map[i, j] < 0.10 or biorthogonality_map[i, j] > 0.10):
                warning_tiles.append({
                    'u_index': int(i),
                    'v_index': int(j),
                    'u': float(grid_u[i]),
                    'v': float(grid_v[j]),
                    'spectral_gap': float(gap_map[i, j]),
                    'biorthogonality_error': float(biorthogonality_map[i, j]),
                })

    modal_plaquette_phase = np.full((rows - 1, cols - 1), np.nan, dtype=float)
    mixing_plaquette = np.full((rows - 1, cols - 1), np.nan, dtype=float)
    for i in range(rows - 1):
        for j in range(cols - 1):
            idxs = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1), (i, j)]
            if any(atlas['ambiguous_map'][ii][jj] for ii, jj in idxs[:-1]):
                continue
            local_frames = [frames[ii][jj] for ii, jj in idxs]
            modal_plaquette_phase[i, j] = mode_wilson_phase(local_frames)
            mixing_plaquette[i, j] = float(np.mean([off_diagonal_mixing_score(a, b) for a, b in zip(local_frames[:-1], local_frames[1:])]))

    metric_trace = np.asarray(scan_payload['metric_trace'], dtype=float)
    operator_softness = np.asarray(scan_payload['operator_softness'], dtype=float)
    gap_vs_metric = _corr(inverse_gap_map.ravel(), metric_trace.ravel())
    gap_vs_softness = _corr(inverse_gap_map.ravel(), operator_softness.ravel())

    payload = {
        'benchmark': benchmark.benchmark_id,
        'control_names': list(benchmark.control_names),
        'grid_u': grid_u.tolist(),
        'grid_v': grid_v.tolist(),
        'spectral_gap_map': gap_map.tolist(),
        'inverse_gap_map': inverse_gap_map.tolist(),
        'biorthogonality_error_map': biorthogonality_map.tolist(),
        'dominant_phase_map': dominant_phase_map.tolist(),
        'modal_plaquette_phase': modal_plaquette_phase.tolist(),
        'modal_mixing_plaquette': mixing_plaquette.tolist(),
        'summaries': {
            'spectral_gap': summarize(gap_map.ravel()),
            'inverse_gap': summarize(inverse_gap_map.ravel()),
            'biorthogonality_error': summarize(biorthogonality_map.ravel()),
            'modal_plaquette_phase_abs': summarize_abs(modal_plaquette_phase.ravel()),
            'modal_mixing_plaquette': summarize(mixing_plaquette.ravel()),
        },
        'correlations': {
            'inverse_gap_vs_metric_trace': gap_vs_metric,
            'inverse_gap_vs_operator_softness': gap_vs_softness,
        },
        'warning_tile_count': len(warning_tiles),
        'warning_tiles': warning_tiles,
        'notes': [
            'Phase 5 uses the auxiliary-operator route, not the full nonlinear Jacobian.',
            'Ambiguous R4 tiles are excluded from modal maps and modal plaquette phases.',
        ],
    }
    out_dir = output_root / benchmark.slug
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f'{benchmark.benchmark_id}_modal_scan.json').write_text(json.dumps(payload, indent=2))
    return payload


def modal_loop_payload(
    benchmark_id: str,
    output_root: Path,
    config: LoopConfig | None = None,
    protocol_name: str | None = None,
    filename: str | None = None,
) -> dict:
    benchmark = get_benchmark(benchmark_id)
    config = config or LoopConfig()
    loop_payload = run_benchmark_loops(benchmark_id, output_root=output_root, config=config, protocol_name=protocol_name)
    run_records = []
    for pair in loop_payload['pair_results']:
        for run in [pair['ccw'], pair['cw']]:
            path = build_loop_path(tuple(run['center']), run['side_length'], run['orientation'], loop_payload['loop_family']['shape'], loop_payload['loop_family']['steps_per_segment'])
            continuation = continue_path_with_branch_ids(benchmark, path, config)
            frames = [biorthogonal_modal_frame(auxiliary_operator_from_state(state)) for state in continuation['states']]
            modal_phase = mode_wilson_phase(frames)
            avg_mixing = float(np.mean([off_diagonal_mixing_score(a, b) for a, b in zip(frames[:-1], frames[1:])])) if len(frames) > 1 else 0.0
            min_gap = float(min(frame.spectral_gap for frame in frames)) if frames else np.nan
            max_biorth_err = float(max(frame.biorthogonality_error for frame in frames)) if frames else np.nan
            run_records.append({
                'center': run['center'],
                'shape': run['shape'],
                'side_length': run['side_length'],
                'orientation': run['orientation'],
                'trusted_r1': run['trusted_r1'],
                'signed_flux': run['signed_flux'],
                'response': run['response'],
                'modal_wilson_phase': modal_phase,
                'avg_modal_mixing': avg_mixing,
                'min_spectral_gap': min_gap,
                'max_biorthogonality_error': max_biorth_err,
            })
    trusted = [run for run in run_records if run['trusted_r1']]
    xs_modal = np.asarray([run['modal_wilson_phase'] for run in trusted], dtype=float)
    xs_flux = np.asarray([run['signed_flux'] for run in trusted], dtype=float)
    ys = np.asarray([run['response'] for run in trusted], dtype=float)
    payload = {
        'benchmark': benchmark.benchmark_id,
        'protocol_name': protocol_name,
        'loop_family': loop_payload['loop_family'],
        'trusted_run_count': int(len(trusted)),
        'runs': run_records,
        'summary': {
            'fit_response_vs_modal_phase': _fit_through_origin(xs_modal, ys),
            'fit_modal_phase_vs_signed_flux': _fit_through_origin(xs_flux, xs_modal),
            'modal_phase_summary': summarize_abs(xs_modal),
            'modal_mixing_summary': summarize([run['avg_modal_mixing'] for run in trusted]),
            'spectral_gap_summary': summarize([run['min_spectral_gap'] for run in trusted]),
            'max_biorthogonality_error': None if not trusted else float(max(run['max_biorthogonality_error'] for run in trusted)),
        },
        'notes': [
            'Modal Wilson phases are computed for the dominant mode of the auxiliary operator along trusted branch-following loops.',
            'Trusted runs inherit the passive R1 filter from the loop layer and exclude R4 branch-switching paths.',
        ],
    }
    out_dir = output_root / benchmark.slug
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / (filename or f'{benchmark.benchmark_id}_modal_loops.json')).write_text(json.dumps(payload, indent=2))
    return payload


def benchmark_modal_payload(benchmark_id: str, output_root: Path, scan_config: ScanConfig | None = None) -> dict:
    scan_payload = modal_scan_payload(benchmark_id, output_root=output_root, scan_config=scan_config)
    loop_payload = modal_loop_payload(benchmark_id, output_root=output_root)
    payload = {
        'benchmark': benchmark_id,
        'scan': scan_payload,
        'loops': loop_payload,
    }
    if benchmark_id == 'benchmark_c':
        payload['patchwise_explanation'] = patchwise_modal_explanation(output_root=output_root)
    out_dir = output_root / get_benchmark(benchmark_id).slug
    (out_dir / f'{benchmark_id}_modal.json').write_text(json.dumps(payload, indent=2))
    return payload


def patchwise_modal_explanation(output_root: Path) -> dict:
    benchmark = get_benchmark('benchmark_c')
    run_robustness_suite('benchmark_c', output_root=output_root)
    center_accumulator: dict[tuple[float, float], dict[str, list[float]]] = {}
    for protocol in protocol_suite('benchmark_c'):
        loops = run_benchmark_loops('benchmark_c', output_root=output_root, config=protocol.config, protocol_name=protocol.name)
        per_center: dict[tuple[float, float], dict[str, list[float]]] = {}
        for pair in loops['pair_results']:
            if not pair['pair_trusted_r1']:
                continue
            center = tuple(pair['center'])
            rec = per_center.setdefault(center, {'modal_phase': [], 'signed_flux': [], 'response': []})
            for run in [pair['ccw'], pair['cw']]:
                path = build_loop_path(center, run['side_length'], run['orientation'], loops['loop_family']['shape'], loops['loop_family']['steps_per_segment'])
                continuation = continue_path_with_branch_ids(benchmark, path, protocol.config)
                frames = [biorthogonal_modal_frame(auxiliary_operator_from_state(state)) for state in continuation['states']]
                rec['modal_phase'].append(mode_wilson_phase(frames))
                rec['signed_flux'].append(run['signed_flux'])
                rec['response'].append(run['response'])
        for center, rec in per_center.items():
            center_accumulator.setdefault(center, {'flux_slope': [], 'modal_slope': [], 'phase_per_flux': []})
            x_flux = np.asarray(rec['signed_flux'], dtype=float)
            x_modal = np.asarray(rec['modal_phase'], dtype=float)
            y = np.asarray(rec['response'], dtype=float)
            center_accumulator[center]['flux_slope'].append(_fit_through_origin(x_flux, y)['slope'])
            center_accumulator[center]['modal_slope'].append(_fit_through_origin(x_modal, y)['slope'])
            center_accumulator[center]['phase_per_flux'].append(_fit_through_origin(x_flux, x_modal)['slope'])

    center_summaries = []
    for center, rec in sorted(center_accumulator.items()):
        flux_slope = float(np.mean([value for value in rec['flux_slope'] if value is not None]))
        modal_slope = float(np.mean([value for value in rec['modal_slope'] if value is not None]))
        phase_per_flux = float(np.mean([value for value in rec['phase_per_flux'] if value is not None]))
        predicted_flux_slope = modal_slope * phase_per_flux
        center_summaries.append({
            'center': [float(center[0]), float(center[1])],
            'mean_response_vs_signed_flux_slope': flux_slope,
            'mean_response_vs_modal_phase_slope': modal_slope,
            'mean_modal_phase_vs_signed_flux_slope': phase_per_flux,
            'predicted_flux_slope_from_modal_factors': predicted_flux_slope,
            'relative_error': None if abs(flux_slope) <= 1e-12 else float(abs(predicted_flux_slope - flux_slope) / abs(flux_slope)),
        })

    observed = np.asarray([item['mean_response_vs_signed_flux_slope'] for item in center_summaries], dtype=float)
    predicted = np.asarray([item['predicted_flux_slope_from_modal_factors'] for item in center_summaries], dtype=float)
    modal_only = np.asarray([item['mean_response_vs_modal_phase_slope'] for item in center_summaries], dtype=float)
    payload = {
        'benchmark': 'benchmark_c',
        'center_summaries': center_summaries,
        'correlations': {
            'observed_vs_predicted_flux_slope': _corr(np.abs(observed), np.abs(predicted)),
            'observed_vs_modal_susceptibility': _corr(np.abs(observed), np.abs(modal_only)),
        },
        'notes': [
            'Patchwise slope variation is decomposed into response-per-modal-phase and modal-phase-per-signed-flux factors.',
            'In the current benchmark C implementation, most center-to-center variation lives in the response-per-modal-phase factor.',
        ],
    }
    out_dir = output_root / benchmark.slug
    (out_dir / 'benchmark_c_modal_patchwise.json').write_text(json.dumps(payload, indent=2))
    return payload
