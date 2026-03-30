from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from cwt.geometry.mixed_state import (
    bures_distance_sq,
    density_from_state,
    offdiag_norm,
    project_to_density,
)

from ._geom_compat import berry_loop_flux, summarize, summarize_abs
from .benchmarks import get_benchmark
from .continuation import continue_path_with_branch_ids
from .loop_protocols import build_loop_path
from .models import LoopConfig, ScanConfig
from .open_system import observable_operator


@dataclass(frozen=True)
class NoisyConfig:
    relaxation: float = 0.35
    depolarizing: float = 0.03
    dephasing_values: tuple[float, ...] = (0.0, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40)
    coherence_switch_ratio: float = 0.45
    metric_mesh: int = 9


def apply_cptp_relaxation(
    rho: np.ndarray, target: np.ndarray, relaxation: float, dephasing: float, depolarizing: float
) -> np.ndarray:
    mixed = (1.0 - relaxation) * rho + relaxation * target
    diag = np.diag(np.diag(mixed))
    mixed = (1.0 - dephasing) * mixed + dephasing * diag
    n = mixed.shape[0]
    mixed = (1.0 - depolarizing) * mixed + depolarizing * np.eye(n, dtype=complex) / n
    return project_to_density(mixed)


def run_noisy_loop(
    benchmark_id: str,
    center: tuple[float, float],
    side: float,
    orientation: str,
    loop_config: LoopConfig,
    noisy_config: NoisyConfig,
    dephasing: float,
) -> dict:
    benchmark = get_benchmark(benchmark_id)
    path = build_loop_path(
        center=center,
        side=side,
        orientation=orientation,
        shape=loop_config.shape,
        steps_per_segment=loop_config.steps_per_segment,
    )
    continuation = continue_path_with_branch_ids(benchmark, path, loop_config)
    states = continuation["states"]
    rho = density_from_state(states[0])
    branch_rhos = [density_from_state(state) for state in states]
    operator = observable_operator(benchmark, states[0])
    actual_samples: list[float] = []
    branch_samples: list[float] = []
    coherence_ratios: list[float] = []

    for target_rho in branch_rhos:
        rho = apply_cptp_relaxation(
            rho=rho,
            target=target_rho,
            relaxation=noisy_config.relaxation,
            dephasing=dephasing,
            depolarizing=noisy_config.depolarizing,
        )
        actual_samples.append(float(np.real(np.trace(rho @ operator))))
        branch_samples.append(float(np.real(np.trace(target_rho @ operator))))
        denom = max(offdiag_norm(target_rho), 1e-12)
        coherence_ratios.append(float(offdiag_norm(rho) / denom))

    if benchmark.primary_observable == "excess_circulation":
        response = float(np.mean(actual_samples) - np.mean(branch_samples))
    else:
        response = float(actual_samples[-1] - branch_samples[-1])

    return {
        "center": [float(center[0]), float(center[1])],
        "side_length": float(side),
        "orientation": orientation,
        "dephasing": float(dephasing),
        "signed_flux": float(berry_loop_flux(states)),
        "response": response,
        "avg_coherence_ratio": float(np.mean(coherence_ratios)) if coherence_ratios else 0.0,
        "final_coherence_ratio": float(coherence_ratios[-1]) if coherence_ratios else 0.0,
        "switch_count": int(continuation["switch_count"]),
        "ambiguous_step_count": int(continuation["ambiguous_step_count"]),
    }


def noisy_scan_level(
    benchmark_id: str, dephasing: float, config: NoisyConfig, scan_config: ScanConfig | None = None
) -> dict:
    benchmark = get_benchmark(benchmark_id)
    scan_cfg = scan_config or ScanConfig(mesh=config.metric_mesh)
    grid_u = np.linspace(*benchmark.control_bounds[0], scan_cfg.mesh, dtype=float)
    grid_v = np.linspace(*benchmark.control_bounds[1], scan_cfg.mesh, dtype=float)
    du = float(grid_u[1] - grid_u[0]) if scan_cfg.mesh > 1 else 1.0
    dv = float(grid_v[1] - grid_v[0]) if scan_cfg.mesh > 1 else 1.0

    rho_grid: list[list[np.ndarray]] = []
    coherence_ratio = np.full((scan_cfg.mesh, scan_cfg.mesh), np.nan, dtype=float)
    for i, u in enumerate(grid_u):
        row: list[np.ndarray] = []
        for j, v in enumerate(grid_v):
            state = benchmark.branch_state_fn(float(u), float(v))
            pure = density_from_state(state)
            noisy = apply_cptp_relaxation(
                rho=pure,
                target=pure,
                relaxation=1.0,
                dephasing=dephasing,
                depolarizing=config.depolarizing,
            )
            row.append(noisy)
            coherence_ratio[i, j] = offdiag_norm(noisy) / max(offdiag_norm(pure), 1e-12)
        rho_grid.append(row)

    bures_metric = np.full((scan_cfg.mesh, scan_cfg.mesh), np.nan, dtype=float)
    for i in range(1, scan_cfg.mesh - 1):
        for j in range(1, scan_cfg.mesh - 1):
            d_u = bures_distance_sq(rho_grid[i + 1][j], rho_grid[i - 1][j]) / max((2.0 * du) ** 2, 1e-12)
            d_v = bures_distance_sq(rho_grid[i][j + 1], rho_grid[i][j - 1]) / max((2.0 * dv) ** 2, 1e-12)
            bures_metric[i, j] = float(d_u + d_v)

    return {
        "dephasing": float(dephasing),
        "grid_u": grid_u.tolist(),
        "grid_v": grid_v.tolist(),
        "bures_metric_trace": bures_metric.tolist(),
        "coherence_ratio": coherence_ratio.tolist(),
        "bures_metric_summary": summarize(bures_metric.ravel()),
        "coherence_ratio_summary": summarize(coherence_ratio.ravel()),
    }


def _fit_through_origin(xs: np.ndarray, ys: np.ndarray) -> dict[str, float | None]:
    if xs.size == 0 or np.allclose(xs, 0.0):
        return {"slope": None, "r2": None, "count": int(xs.size)}
    slope = float(np.dot(xs, ys) / np.dot(xs, xs))
    residual = ys - slope * xs
    denom = float(np.dot(ys, ys))
    r2 = None if denom <= 1e-15 else float(1.0 - np.dot(residual, residual) / denom)
    return {"slope": slope, "r2": r2, "count": int(xs.size)}


def noisy_benchmark_payload(
    benchmark_id: str,
    output_root: Path,
    loop_config: LoopConfig | None = None,
    noisy_config: NoisyConfig | None = None,
    scan_config: ScanConfig | None = None,
) -> dict:
    benchmark = get_benchmark(benchmark_id)
    loop_cfg = loop_config or LoopConfig()
    noisy_cfg = noisy_config or NoisyConfig()
    scan_cfg = scan_config or ScanConfig(mesh=noisy_cfg.metric_mesh)

    scan_levels = [
        noisy_scan_level(benchmark_id, dephasing=gamma, config=noisy_cfg, scan_config=scan_cfg)
        for gamma in noisy_cfg.dephasing_values
    ]

    loop_levels: list[dict] = []
    for gamma in noisy_cfg.dephasing_values:
        runs = []
        pairs = []
        for center in benchmark.default_loop_centers:
            for side in benchmark.default_loop_side_lengths:
                ccw = run_noisy_loop(
                    benchmark_id=benchmark_id,
                    center=center,
                    side=side,
                    orientation="ccw",
                    loop_config=loop_cfg,
                    noisy_config=noisy_cfg,
                    dephasing=gamma,
                )
                cw = run_noisy_loop(
                    benchmark_id=benchmark_id,
                    center=center,
                    side=side,
                    orientation="cw",
                    loop_config=loop_cfg,
                    noisy_config=noisy_cfg,
                    dephasing=gamma,
                )
                runs.extend([ccw, cw])
                pairs.append(
                    {
                        "center": [float(center[0]), float(center[1])],
                        "side_length": float(side),
                        "flux_magnitude": float(abs(ccw["signed_flux"])),
                        "orientation_gap": float(ccw["response"] - cw["response"]),
                        "mean_coherence_ratio": float(
                            0.5 * (ccw["avg_coherence_ratio"] + cw["avg_coherence_ratio"])
                        ),
                    }
                )
        xs = np.asarray([run["signed_flux"] for run in runs], dtype=float)
        ys = np.asarray([run["response"] for run in runs], dtype=float)
        pair_x = np.asarray([row["flux_magnitude"] for row in pairs], dtype=float)
        pair_y = np.asarray([row["orientation_gap"] for row in pairs], dtype=float)
        grouped: dict[tuple[float, float], list[dict]] = {}
        for row in pairs:
            grouped.setdefault(tuple(row["center"]), []).append(row)
        by_center = []
        for center, local_rows in sorted(grouped.items()):
            cx = np.asarray([row["flux_magnitude"] for row in local_rows], dtype=float)
            cy = np.asarray([row["orientation_gap"] for row in local_rows], dtype=float)
            by_center.append(
                {
                    "center": [float(center[0]), float(center[1])],
                    "fit_orientation_gap_vs_abs_flux": _fit_through_origin(cx, cy),
                    "coherence_ratio_summary": summarize([row["mean_coherence_ratio"] for row in local_rows]),
                }
            )
        loop_levels.append(
            {
                "dephasing": float(gamma),
                "runs": runs,
                "pairs": pairs,
                "fit_response_vs_signed_flux": _fit_through_origin(xs, ys),
                "fit_orientation_gap_vs_abs_flux": _fit_through_origin(pair_x, pair_y),
                "response_summary": summarize_abs(ys),
                "orientation_gap_summary": summarize_abs(pair_y),
                "coherence_ratio_summary": summarize([run["avg_coherence_ratio"] for run in runs]),
                "by_center": by_center,
            }
        )

    recommended_switch = noisy_cfg.dephasing_values[-1]
    for level in loop_levels:
        if float(level["coherence_ratio_summary"]["mean"] or 0.0) <= noisy_cfg.coherence_switch_ratio:
            recommended_switch = float(level["dephasing"])
            break

    payload = {
        "benchmark": benchmark.benchmark_id,
        "dephasing_levels": [float(x) for x in noisy_cfg.dephasing_values],
        "scan_levels": scan_levels,
        "loop_levels": loop_levels,
        "recommended_switch_dephasing": float(recommended_switch),
        "switch_rule": f"switch when mean loop coherence ratio <= {noisy_cfg.coherence_switch_ratio:.2f}",
        "notes": [
            "This lane uses an explicit CPTP relaxation/dephasing/depolarizing update on density matrices.",
            "Scan-side geometry currently reports Bures-metric traces and coherence ratios; a full"
            " Uhlmann-curvature implementation remains future work.",
            "Loop-side results are reported both globally and patchwise by center. In the ring benchmark,"
            " the patchwise orientation-gap law is stronger than the global response-vs-flux fit.",
        ],
    }

    out_dir = output_root / benchmark.slug
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{benchmark.benchmark_id}_noisy.json").write_text(json.dumps(payload, indent=2))
    return payload
