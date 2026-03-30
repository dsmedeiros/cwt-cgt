from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from .._geom_compat import summarize, summarize_abs
from ..benchmarks import get_benchmark
from ..continuation import build_branch_atlas, continue_path_with_branch_ids
from ..jacobian import (
    JacobianConfig,
    control_coupling_vectors,
    jacobian_diagnostics,
    jacobian_modal_frame,
    numerical_branch_jacobian,
    response_metric_trace_and_curvature,
    solve_branch_response,
)
from ..loop_protocols import build_loop_path, run_benchmark_loops
from ..modal import mode_wilson_phase, off_diagonal_mixing_score
from ..models import LoopConfig, ScanConfig
from ..robustness import protocol_suite, run_robustness_suite
from ..runner import run_benchmark_scan


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


def _reference_state(benchmark, u: float, v: float, branch_id: str):
    candidate = benchmark.resolve_candidate_by_id(u, v, branch_id)
    if candidate is not None:
        return candidate.state
    return benchmark.branch_state_fn(u, v)


def _cache_key(benchmark_id: str, u: float, v: float, branch_id: str) -> tuple[str, float, float, str]:
    return (benchmark_id, round(float(u), 6), round(float(v), 6), str(branch_id))


def _bundle_for_point(
    benchmark,
    u: float,
    v: float,
    branch_id: str,
    config: JacobianConfig,
    cache: dict[tuple[str, float, float, str], dict[str, Any]],
) -> dict[str, Any]:
    key = _cache_key(benchmark.benchmark_id, u, v, branch_id)
    if key in cache:
        return cache[key]

    state = _reference_state(benchmark, float(u), float(v), branch_id)
    jac = numerical_branch_jacobian(state, config=config)
    bu, bv = control_coupling_vectors(benchmark, u=float(u), v=float(v), branch_id=branch_id, reference_state=state, config=config)
    du = solve_branch_response(jac, bu)
    dv = solve_branch_response(jac, bv)
    metric_pred, curvature_pred = response_metric_trace_and_curvature(state, du, dv)
    diag = jacobian_diagnostics(jac)
    frame = jacobian_modal_frame(jac)
    bundle = {
        'state': state,
        'jacobian': jac,
        'bu': bu,
        'bv': bv,
        'du': du,
        'dv': dv,
        'metric_pred': float(metric_pred),
        'curvature_pred': float(curvature_pred),
        'diagnostics': diag,
        'frame': frame,
    }
    cache[key] = bundle
    return bundle


def jacobian_scan_payload(
    benchmark_id: str,
    output_root: Path,
    scan_config: ScanConfig | None = None,
    jacobian_config: JacobianConfig | None = None,
) -> dict:
    scan_config = scan_config or ScanConfig()
    jac_config = jacobian_config or JacobianConfig()
    benchmark = get_benchmark(benchmark_id)
    scan_payload = run_benchmark_scan(benchmark_id, output_root=output_root, config=scan_config)
    grid_u = np.asarray(scan_payload['grid_u'], dtype=float)
    grid_v = np.asarray(scan_payload['grid_v'], dtype=float)
    atlas = build_branch_atlas(benchmark, grid_u, grid_v, scan_config)
    rows, cols = grid_u.size, grid_v.size
    cache: dict[tuple[str, float, float, str], dict[str, Any]] = {}

    metric_pred = np.full((rows, cols), np.nan, dtype=float)
    curvature_pred = np.full((rows, cols), np.nan, dtype=float)
    spectral_radius = np.full((rows, cols), np.nan, dtype=float)
    inv_min_singular = np.full((rows, cols), np.nan, dtype=float)
    nonnormality = np.full((rows, cols), np.nan, dtype=float)
    control_norm_u = np.full((rows, cols), np.nan, dtype=float)
    control_norm_v = np.full((rows, cols), np.nan, dtype=float)
    dominant_phase = np.full((rows, cols), np.nan, dtype=float)
    modal_plaquette_phase = np.full((rows - 1, cols - 1), np.nan, dtype=float)
    mixing_plaquette = np.full((rows - 1, cols - 1), np.nan, dtype=float)

    warning_tiles: list[dict[str, float | int | bool | str]] = []

    for i, u in enumerate(grid_u):
        for j, v in enumerate(grid_v):
            if atlas['ambiguous_map'][i][j]:
                continue
            branch_id = atlas['chosen_branch_id_map'][i][j]
            bundle = _bundle_for_point(benchmark, float(u), float(v), branch_id, jac_config, cache)
            metric_pred[i, j] = bundle['metric_pred']
            curvature_pred[i, j] = bundle['curvature_pred']
            spectral_radius[i, j] = bundle['diagnostics'].spectral_radius
            inv_min_singular[i, j] = bundle['diagnostics'].inverse_min_singular_i_minus_m
            nonnormality[i, j] = bundle['diagnostics'].nonnormality_ratio
            control_norm_u[i, j] = float(np.linalg.norm(bundle['du']))
            control_norm_v[i, j] = float(np.linalg.norm(bundle['dv']))
            dominant_phase[i, j] = float(np.angle(bundle['diagnostics'].dominant_eigenvalue))
            if bundle['diagnostics'].spectral_radius > 0.98 or bundle['diagnostics'].inverse_min_singular_i_minus_m > 15.0:
                warning_tiles.append(
                    {
                        'u_index': int(i),
                        'v_index': int(j),
                        'u': float(u),
                        'v': float(v),
                        'branch_id': branch_id,
                        'spectral_radius': float(bundle['diagnostics'].spectral_radius),
                        'inverse_min_singular_i_minus_m': float(bundle['diagnostics'].inverse_min_singular_i_minus_m),
                        'nonnormality_ratio': float(bundle['diagnostics'].nonnormality_ratio),
                        'stable': bool(bundle['diagnostics'].stable),
                    }
                )

    for i in range(rows - 1):
        for j in range(cols - 1):
            idxs = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1), (i, j)]
            if any(atlas['ambiguous_map'][ii][jj] for ii, jj in idxs[:-1]):
                continue
            frames = []
            for ii, jj in idxs:
                branch_id = atlas['chosen_branch_id_map'][ii][jj]
                frames.append(_bundle_for_point(benchmark, float(grid_u[ii]), float(grid_v[jj]), branch_id, jac_config, cache)['frame'])
            modal_plaquette_phase[i, j] = mode_wilson_phase(frames)
            mixing_plaquette[i, j] = float(np.mean([off_diagonal_mixing_score(a, b) for a, b in zip(frames[:-1], frames[1:])]))

    metric_ref = np.asarray(scan_payload['metric_trace'], dtype=float)
    curvature_ref = np.asarray(scan_payload['curvature'], dtype=float)
    predicted_curv_trim = curvature_pred[:-1, :-1]
    payload = {
        'benchmark': benchmark.benchmark_id,
        'control_names': list(benchmark.control_names),
        'grid_u': grid_u.tolist(),
        'grid_v': grid_v.tolist(),
        'metric_trace_predicted': metric_pred.tolist(),
        'curvature_predicted': curvature_pred.tolist(),
        'spectral_radius_map': spectral_radius.tolist(),
        'inverse_min_singular_i_minus_m_map': inv_min_singular.tolist(),
        'nonnormality_ratio_map': nonnormality.tolist(),
        'control_response_norm_u': control_norm_u.tolist(),
        'control_response_norm_v': control_norm_v.tolist(),
        'dominant_eigenphase_map': dominant_phase.tolist(),
        'jacobian_modal_plaquette_phase': modal_plaquette_phase.tolist(),
        'jacobian_modal_mixing_plaquette': mixing_plaquette.tolist(),
        'summaries': {
            'metric_trace_predicted': summarize(metric_pred.ravel()),
            'curvature_predicted_abs': summarize_abs(curvature_pred.ravel()),
            'spectral_radius': summarize(spectral_radius.ravel()),
            'inverse_min_singular_i_minus_m': summarize(inv_min_singular.ravel()),
            'nonnormality_ratio': summarize(nonnormality.ravel()),
            'jacobian_modal_plaquette_phase_abs': summarize_abs(modal_plaquette_phase.ravel()),
        },
        'correlations': {
            'predicted_metric_vs_state_metric': _corr(metric_pred.ravel(), metric_ref.ravel()),
            'predicted_curvature_vs_state_curvature': _corr(predicted_curv_trim.ravel(), curvature_ref.ravel()),
            'inverse_min_singular_vs_state_metric': _corr(inv_min_singular.ravel(), metric_ref.ravel()),
            'nonnormality_vs_state_metric': _corr(nonnormality.ravel(), metric_ref.ravel()),
        },
        'warning_tile_count': int(len(warning_tiles)),
        'warning_tiles': warning_tiles,
        'notes': [
            'Phase 6 uses the explicit numerical Jacobian of the branch-local relaxation map, not the earlier auxiliary modal surrogate.',
            'Ambiguous R4 tiles are excluded from Jacobian scan maps and Jacobian modal plaquette phases.',
        ],
    }
    out_dir = output_root / benchmark.slug
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f'{benchmark.benchmark_id}_jacobian_scan.json').write_text(json.dumps(payload, indent=2))
    return payload


def _centerwise_fit(runs: list[dict], x_key: str, y_key: str = 'response') -> list[dict]:
    grouped: dict[tuple[float, float], list[dict]] = {}
    for run in runs:
        grouped.setdefault(tuple(run['center']), []).append(run)
    summaries = []
    for center, local_runs in sorted(grouped.items()):
        trusted = [run for run in local_runs if run['trusted_r1']]
        x = np.asarray([run[x_key] for run in trusted], dtype=float)
        y = np.asarray([run[y_key] for run in trusted], dtype=float)
        summaries.append(
            {
                'center': [float(center[0]), float(center[1])],
                'trusted_run_count': int(len(trusted)),
                f'fit_{y_key}_vs_{x_key}': _fit_through_origin(x, y),
            }
        )
    return summaries


def jacobian_loop_payload(
    benchmark_id: str,
    output_root: Path,
    config: LoopConfig | None = None,
    jacobian_config: JacobianConfig | None = None,
    protocol_name: str | None = None,
    filename: str | None = None,
) -> dict:
    benchmark = get_benchmark(benchmark_id)
    loop_config = config or LoopConfig()
    jac_config = jacobian_config or JacobianConfig()
    cache: dict[tuple[str, float, float, str], dict[str, Any]] = {}
    loop_payload = run_benchmark_loops(benchmark_id, output_root=output_root, config=loop_config, protocol_name=protocol_name, filename=f'{benchmark_id}_loops.json')
    run_records = []
    for pair in loop_payload['pair_results']:
        for run in [pair['ccw'], pair['cw']]:
            center = tuple(run['center'])
            path = build_loop_path(center, run['side_length'], run['orientation'], loop_payload['loop_family']['shape'], loop_payload['loop_family']['steps_per_segment'])
            continuation = continue_path_with_branch_ids(benchmark, path, loop_config)
            frames = []
            path_curvatures = []
            inv_min = []
            spec_radius = []
            nonnormal = []
            for (u, v), branch_id in zip(path, continuation['branch_ids']):
                bundle = _bundle_for_point(benchmark, float(u), float(v), branch_id, jac_config, cache)
                frames.append(bundle['frame'])
                path_curvatures.append(bundle['curvature_pred'])
                inv_min.append(bundle['diagnostics'].inverse_min_singular_i_minus_m)
                spec_radius.append(bundle['diagnostics'].spectral_radius)
                nonnormal.append(bundle['diagnostics'].nonnormality_ratio)
            center_bundle = _bundle_for_point(benchmark, float(center[0]), float(center[1]), benchmark.canonical_branch_id, jac_config, cache)
            predicted_flux_center = float(center_bundle['curvature_pred'] * run['signed_area'])
            predicted_flux_pathmean = float(np.mean(path_curvatures) * run['signed_area']) if path_curvatures else 0.0
            jacobian_phase = mode_wilson_phase(frames)
            avg_mixing = float(np.mean([off_diagonal_mixing_score(a, b) for a, b in zip(frames[:-1], frames[1:])])) if len(frames) > 1 else 0.0
            run_records.append(
                {
                    'center': run['center'],
                    'shape': run['shape'],
                    'side_length': run['side_length'],
                    'orientation': run['orientation'],
                    'trusted_r1': run['trusted_r1'],
                    'signed_flux': run['signed_flux'],
                    'response': run['response'],
                    'predicted_signed_flux_center': predicted_flux_center,
                    'predicted_signed_flux_pathmean': predicted_flux_pathmean,
                    'jacobian_modal_phase': jacobian_phase,
                    'avg_jacobian_modal_mixing': avg_mixing,
                    'max_spectral_radius': float(np.max(spec_radius)) if spec_radius else np.nan,
                    'max_inverse_min_singular_i_minus_m': float(np.max(inv_min)) if inv_min else np.nan,
                    'mean_nonnormality_ratio': float(np.mean(nonnormal)) if nonnormal else np.nan,
                }
            )
    trusted = [run for run in run_records if run['trusted_r1']]
    xs_pred = np.asarray([run['predicted_signed_flux_pathmean'] for run in trusted], dtype=float)
    xs_flux = np.asarray([run['signed_flux'] for run in trusted], dtype=float)
    xs_phase = np.asarray([run['jacobian_modal_phase'] for run in trusted], dtype=float)
    ys = np.asarray([run['response'] for run in trusted], dtype=float)
    payload = {
        'benchmark': benchmark.benchmark_id,
        'protocol_name': protocol_name,
        'loop_family': loop_payload['loop_family'],
        'trusted_run_count': int(len(trusted)),
        'runs': run_records,
        'summary': {
            'fit_response_vs_predicted_signed_flux': _fit_through_origin(xs_pred, ys),
            'fit_predicted_signed_flux_vs_state_signed_flux': _fit_through_origin(xs_flux, xs_pred),
            'fit_response_vs_jacobian_modal_phase': _fit_through_origin(xs_phase, ys),
            'fit_jacobian_modal_phase_vs_signed_flux': _fit_through_origin(xs_flux, xs_phase),
            'fit_response_vs_predicted_signed_flux_by_center': _centerwise_fit(run_records, 'predicted_signed_flux_pathmean', 'response'),
            'fit_predicted_signed_flux_vs_state_signed_flux_by_center': _centerwise_fit(run_records, 'signed_flux', 'predicted_signed_flux_pathmean'),
            'predicted_signed_flux_summary': summarize_abs(xs_pred),
            'jacobian_modal_phase_summary': summarize_abs(xs_phase),
            'jacobian_modal_mixing_summary': summarize([run['avg_jacobian_modal_mixing'] for run in trusted]),
            'max_spectral_radius_summary': summarize([run['max_spectral_radius'] for run in trusted]),
            'max_inverse_min_singular_i_minus_m_summary': summarize([run['max_inverse_min_singular_i_minus_m'] for run in trusted]),
            'mean_nonnormality_ratio_summary': summarize([run['mean_nonnormality_ratio'] for run in trusted]),
        },
        'notes': [
            'Predicted signed flux uses the path-mean Jacobian-derived curvature multiplied by the signed loop area.',
            'Jacobian modal phases are retained as a secondary diagnostic but are weaker than the derived predicted-flux law in the current implementation.',
        ],
    }
    out_dir = output_root / benchmark.slug
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / (filename or f'{benchmark.benchmark_id}_jacobian_loops.json')).write_text(json.dumps(payload, indent=2))
    return payload


def patchwise_jacobian_explanation(output_root: Path, jacobian_config: JacobianConfig | None = None) -> dict:
    jac_config = jacobian_config or JacobianConfig()
    benchmark = get_benchmark('benchmark_c')
    run_robustness_suite('benchmark_c', output_root=output_root)
    cache: dict[tuple[str, float, float, str], dict[str, Any]] = {}
    center_accumulator: dict[tuple[float, float], dict[str, list[float]]] = {}
    for protocol in protocol_suite('benchmark_c'):
        loops = run_benchmark_loops('benchmark_c', output_root=output_root, config=protocol.config, protocol_name=protocol.name, filename=protocol.filename)
        per_center: dict[tuple[float, float], dict[str, list[float]]] = {}
        for pair in loops['pair_results']:
            if not pair['pair_trusted_r1']:
                continue
            center = tuple(pair['center'])
            rec = per_center.setdefault(center, {'pred_flux': [], 'state_flux': [], 'response': []})
            for run in [pair['ccw'], pair['cw']]:
                path = build_loop_path(center, run['side_length'], run['orientation'], loops['loop_family']['shape'], loops['loop_family']['steps_per_segment'])
                continuation = continue_path_with_branch_ids(benchmark, path, protocol.config)
                path_curvatures = []
                for (u, v), branch_id in zip(path, continuation['branch_ids']):
                    path_curvatures.append(_bundle_for_point(benchmark, float(u), float(v), branch_id, jac_config, cache)['curvature_pred'])
                rec['pred_flux'].append(float(np.mean(path_curvatures) * run['signed_area']))
                rec['state_flux'].append(run['signed_flux'])
                rec['response'].append(run['response'])
        for center, rec in per_center.items():
            center_accumulator.setdefault(center, {'resp_vs_pred': [], 'pred_vs_state': [], 'resp_vs_state': []})
            pred_flux = np.asarray(rec['pred_flux'], dtype=float)
            state_flux = np.asarray(rec['state_flux'], dtype=float)
            response = np.asarray(rec['response'], dtype=float)
            center_accumulator[center]['resp_vs_pred'].append(_fit_through_origin(pred_flux, response)['slope'])
            center_accumulator[center]['pred_vs_state'].append(_fit_through_origin(state_flux, pred_flux)['slope'])
            center_accumulator[center]['resp_vs_state'].append(_fit_through_origin(state_flux, response)['slope'])

    center_summaries = []
    for center, rec in sorted(center_accumulator.items()):
        resp_vs_pred = float(np.mean([value for value in rec['resp_vs_pred'] if value is not None]))
        pred_vs_state = float(np.mean([value for value in rec['pred_vs_state'] if value is not None]))
        resp_vs_state = float(np.mean([value for value in rec['resp_vs_state'] if value is not None]))
        reconstructed = resp_vs_pred * pred_vs_state
        center_summaries.append(
            {
                'center': [float(center[0]), float(center[1])],
                'mean_response_vs_predicted_flux_slope': resp_vs_pred,
                'mean_predicted_flux_vs_state_flux_slope': pred_vs_state,
                'mean_response_vs_state_flux_slope': resp_vs_state,
                'reconstructed_response_vs_state_flux_slope': reconstructed,
                'relative_error': None if abs(resp_vs_state) <= 1e-12 else float(abs(reconstructed - resp_vs_state) / abs(resp_vs_state)),
            }
        )

    observed = np.asarray([item['mean_response_vs_state_flux_slope'] for item in center_summaries], dtype=float)
    reconstructed = np.asarray([item['reconstructed_response_vs_state_flux_slope'] for item in center_summaries], dtype=float)
    payload = {
        'benchmark': 'benchmark_c',
        'center_summaries': center_summaries,
        'correlations': {
            'observed_vs_reconstructed_state_flux_slope': _corr(np.abs(observed), np.abs(reconstructed)),
        },
        'notes': [
            'Patchwise signed-loop slopes are decomposed into a response-vs-predicted-flux factor and a predicted-flux-vs-state-flux factor.',
            'This is the main explanatory result of the explicit Jacobian route in the current implementation.',
        ],
    }
    out_dir = output_root / benchmark.slug
    (out_dir / 'benchmark_c_jacobian_patchwise.json').write_text(json.dumps(payload, indent=2))
    return payload


def benchmark_jacobian_payload(
    benchmark_id: str,
    output_root: Path,
    scan_config: ScanConfig | None = None,
    loop_config: LoopConfig | None = None,
    jacobian_config: JacobianConfig | None = None,
) -> dict:
    scan_payload = jacobian_scan_payload(benchmark_id, output_root=output_root, scan_config=scan_config, jacobian_config=jacobian_config)
    loop_payload = jacobian_loop_payload(benchmark_id, output_root=output_root, config=loop_config, jacobian_config=jacobian_config)
    payload = {'benchmark': benchmark_id, 'scan': scan_payload, 'loops': loop_payload}
    if benchmark_id == 'benchmark_c':
        payload['patchwise_explanation'] = patchwise_jacobian_explanation(output_root=output_root, jacobian_config=jacobian_config)
    out_dir = output_root / get_benchmark(benchmark_id).slug
    (out_dir / f'{benchmark_id}_jacobian.json').write_text(json.dumps(payload, indent=2))
    return payload
