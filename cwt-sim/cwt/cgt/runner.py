from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from ._geom_compat import (
    berry_loop_flux,
    overlap,
    phase_coherence,
    projective_metric_trace_and_curvature,
    psi_from_state,
    summarize,
    summarize_abs,
)
from .benchmarks import get_benchmark
from .loop_protocols import run_benchmark_loops
from .models import LoopConfig, ScanConfig


def _grid(bounds: tuple[float, float], mesh: int) -> np.ndarray:
    return np.linspace(bounds[0], bounds[1], mesh, dtype=float)


def _nan_grid(mesh: int) -> np.ndarray:
    return np.full((mesh, mesh), np.nan, dtype=float)


def _regime_label(avg_overlap: float, coherence: float, config: ScanConfig) -> str:
    if avg_overlap < config.overlap_floor or coherence < config.coherence_floor:
        return 'R3'
    return 'R1'


def run_benchmark_scan(benchmark_id: str, output_root: Path, config: ScanConfig | None = None) -> dict:
    scan_config = config or ScanConfig()
    benchmark = get_benchmark(benchmark_id)
    grid_u = _grid(benchmark.control_bounds[0], scan_config.mesh)
    grid_v = _grid(benchmark.control_bounds[1], scan_config.mesh)
    du = float(grid_u[1] - grid_u[0]) if scan_config.mesh > 1 else 1.0
    dv = float(grid_v[1] - grid_v[0]) if scan_config.mesh > 1 else 1.0

    states: list[list] = []
    coherence = _nan_grid(scan_config.mesh)
    avg_overlap = _nan_grid(scan_config.mesh)
    metric_trace = _nan_grid(scan_config.mesh)
    operator_softness = _nan_grid(scan_config.mesh)
    max_multiplier = _nan_grid(scan_config.mesh)
    regime_map = [['unresolved' for _ in range(scan_config.mesh)] for _ in range(scan_config.mesh)]

    for i, u in enumerate(grid_u):
        row = []
        for j, v in enumerate(grid_v):
            state = benchmark.branch_state_fn(float(u), float(v))
            row.append(state)
            coherence[i, j] = phase_coherence(state)
            softness = benchmark.softness_fn(float(u), float(v))
            operator_softness[i, j] = softness
            max_multiplier[i, j] = 1.0 - 1.0 / max(softness, 1.0)
        states.append(row)

    for i in range(scan_config.mesh):
        for j in range(scan_config.mesh):
            psi_here = psi_from_state(states[i][j])
            overlaps = []
            if i + 1 < scan_config.mesh:
                overlaps.append(overlap(psi_here, psi_from_state(states[i + 1][j])))
            if i - 1 >= 0:
                overlaps.append(overlap(psi_here, psi_from_state(states[i - 1][j])))
            if j + 1 < scan_config.mesh:
                overlaps.append(overlap(psi_here, psi_from_state(states[i][j + 1])))
            if j - 1 >= 0:
                overlaps.append(overlap(psi_here, psi_from_state(states[i][j - 1])))
            avg_overlap[i, j] = float(np.mean(overlaps)) if overlaps else math.nan
            regime_map[i][j] = _regime_label(avg_overlap=float(avg_overlap[i, j]), coherence=float(coherence[i, j]), config=scan_config)

    for i in range(1, scan_config.mesh - 1):
        for j in range(1, scan_config.mesh - 1):
            psi0 = psi_from_state(states[i][j])
            metric, _ = projective_metric_trace_and_curvature(
                psi0=psi0,
                psi_u_plus=psi_from_state(states[i + 1][j]),
                psi_u_minus=psi_from_state(states[i - 1][j]),
                psi_v_plus=psi_from_state(states[i][j + 1]),
                psi_v_minus=psi_from_state(states[i][j - 1]),
                du=du,
                dv=dv,
            )
            metric_trace[i, j] = metric

    curvature = np.full((scan_config.mesh - 1, scan_config.mesh - 1), np.nan, dtype=float)
    for i in range(scan_config.mesh - 1):
        for j in range(scan_config.mesh - 1):
            # Counter-clockwise plaquette orientation.
            plaquette_states = [
                states[i][j],
                states[i + 1][j],
                states[i + 1][j + 1],
                states[i][j + 1],
                states[i][j],
            ]
            flux = berry_loop_flux(plaquette_states)
            curvature[i, j] = flux / (du * dv)

    regime_counts: dict[str, int] = {}
    for row in regime_map:
        for label in row:
            regime_counts[label] = regime_counts.get(label, 0) + 1

    payload = {
        'benchmark': benchmark.benchmark_id,
        'description': benchmark.description,
        'expected_behavior': benchmark.expected_behavior,
        'expected_regime': benchmark.expected_regime,
        'control_names': list(benchmark.control_names),
        'grid_u': grid_u.tolist(),
        'grid_v': grid_v.tolist(),
        'coherence': coherence.tolist(),
        'avg_overlap': avg_overlap.tolist(),
        'metric_trace': metric_trace.tolist(),
        'curvature': curvature.tolist(),
        'operator_softness': operator_softness.tolist(),
        'max_multiplier': max_multiplier.tolist(),
        'regime_map': regime_map,
        'metric_summary': summarize(metric_trace.ravel()),
        'curvature_summary': summarize_abs(curvature.ravel()),
        'regime_summary': regime_counts,
        'notes': 'Passive analytic branch scan for the hardened benchmark scaffold. Loop protocols are stored in a separate *_loops.json artifact.',
    }
    benchmark_dir = output_root / benchmark.slug
    benchmark_dir.mkdir(parents=True, exist_ok=True)
    output_path = benchmark_dir / f'{benchmark.benchmark_id}_scan.json'
    output_path.write_text(json.dumps(payload, indent=2))
    return payload


def run_benchmark_all(
    benchmark_id: str,
    output_root: Path,
    scan_config: ScanConfig | None = None,
    loop_config: LoopConfig | None = None,
) -> dict:
    scan_payload = run_benchmark_scan(benchmark_id=benchmark_id, output_root=output_root, config=scan_config)
    loop_payload = run_benchmark_loops(benchmark_id=benchmark_id, output_root=output_root, config=loop_config)
    return {'scan': scan_payload, 'loops': loop_payload}
