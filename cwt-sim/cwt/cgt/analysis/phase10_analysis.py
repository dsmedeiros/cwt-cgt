from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from cwt.geometry.mixed_state import (
    bures_distance_sq,
    mixed_loop_holonomy_phase,
    mixed_plaquette_curvature,
    purity,
)

from .._geom_compat import summarize, summarize_abs
from ..benchmarks import get_benchmark
from ..continuation import build_branch_atlas, continue_path_with_branch_ids
from ..loop_protocols import build_loop_path
from ..models import LoopConfig, ScanConfig
from ..open_system import (
    OpenSystemConfig,
    apply_local_open_step,
    coherence_ratio,
    effective_branch_density,
    observable_operator,
)


@dataclass(frozen=True)
class Phase10Config:
    benchmark_id: str = "benchmark_c"
    scan_mesh: int = 9
    dephasing_values: tuple[float, ...] = (0.0, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40)
    coherence_switch_floor: float = 0.20
    output_plot_dirname: str = "phase10"


def _fit_through_origin(xs: np.ndarray, ys: np.ndarray) -> dict[str, float | int | None]:
    if xs.size == 0 or np.allclose(xs, 0.0):
        return {"slope": None, "r2": None, "count": int(xs.size)}
    slope = float(np.dot(xs, ys) / np.dot(xs, xs))
    residual = ys - slope * xs
    denom = float(np.dot(ys, ys))
    r2 = None if denom <= 1e-15 else float(1.0 - np.dot(residual, residual) / denom)
    return {"slope": slope, "r2": r2, "count": int(xs.size)}


def _state_signature(state) -> tuple[float, ...]:
    return tuple(
        np.round(np.concatenate([state.p.ravel(), state.theta.ravel(), state.kernel.ravel()]), 10).tolist()
    )


class FixedPointCache:
    def __init__(self, config: OpenSystemConfig):
        self.config = config
        self._cache: dict[tuple[float, tuple[float, ...]], np.ndarray] = {}

    def get(self, state, dephasing: float) -> np.ndarray:
        key = (round(float(dephasing), 6), _state_signature(state))
        if key not in self._cache:
            self._cache[key] = effective_branch_density(state, config=self.config, dephasing=float(dephasing))
        return self._cache[key]


def _bures_metric_trace(rho_grid: list[list[np.ndarray]], du: float, dv: float) -> np.ndarray:
    mesh = len(rho_grid)
    metric = np.full((mesh, mesh), np.nan, dtype=float)
    for i in range(1, mesh - 1):
        for j in range(1, mesh - 1):
            d_u = bures_distance_sq(rho_grid[i + 1][j], rho_grid[i - 1][j]) / max((2.0 * du) ** 2, 1e-12)
            d_v = bures_distance_sq(rho_grid[i][j + 1], rho_grid[i][j - 1]) / max((2.0 * dv) ** 2, 1e-12)
            metric[i, j] = float(d_u + d_v)
    return metric


def _mixed_curvature_grid(
    rho_grid: list[list[np.ndarray]], ambiguous_map: list[list[bool]], du: float, dv: float
) -> np.ndarray:
    mesh = len(rho_grid)
    curv = np.full((mesh - 1, mesh - 1), np.nan, dtype=float)
    area = du * dv
    for i in range(mesh - 1):
        for j in range(mesh - 1):
            if any(
                [
                    ambiguous_map[i][j],
                    ambiguous_map[i + 1][j],
                    ambiguous_map[i + 1][j + 1],
                    ambiguous_map[i][j + 1],
                ]
            ):
                continue
            curv[i, j] = mixed_plaquette_curvature(
                rho_grid[i][j], rho_grid[i + 1][j], rho_grid[i + 1][j + 1], rho_grid[i][j + 1], area
            )
    return curv


def _scan_level(
    benchmark_id: str,
    scan_config: ScanConfig,
    open_config: OpenSystemConfig,
    cache: FixedPointCache,
    dephasing: float,
) -> dict:
    benchmark = get_benchmark(benchmark_id)
    grid_u = np.linspace(*benchmark.control_bounds[0], scan_config.mesh, dtype=float)
    grid_v = np.linspace(*benchmark.control_bounds[1], scan_config.mesh, dtype=float)
    du = float(grid_u[1] - grid_u[0]) if scan_config.mesh > 1 else 1.0
    dv = float(grid_v[1] - grid_v[0]) if scan_config.mesh > 1 else 1.0
    atlas = build_branch_atlas(benchmark=benchmark, grid_u=grid_u, grid_v=grid_v, config=scan_config)
    states = atlas["chosen_states"]

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

    metric = _bures_metric_trace(rho_grid, du=du, dv=dv)
    curvature = _mixed_curvature_grid(rho_grid, atlas["ambiguous_map"], du=du, dv=dv)
    trusted_curvature = np.abs(curvature[np.isfinite(curvature)])
    mean_abs_curvature = float(np.mean(trusted_curvature)) if trusted_curvature.size else 0.0
    return {
        "dephasing": float(dephasing),
        "grid_u": grid_u.tolist(),
        "grid_v": grid_v.tolist(),
        "bures_metric_trace": metric.tolist(),
        "mixed_curvature": curvature.tolist(),
        "coherence_ratio": coherence_grid.tolist(),
        "purity": purity_grid.tolist(),
        "metric_summary": summarize(metric.ravel()),
        "mixed_curvature_summary": summarize_abs(curvature.ravel()),
        "coherence_ratio_summary": summarize(coherence_grid.ravel()),
        "purity_summary": summarize(purity_grid.ravel()),
        "mean_abs_mixed_curvature": mean_abs_curvature,
        "ambiguous_tile_count": int(sum(sum(1 for flag in row if flag) for row in atlas["ambiguous_map"])),
    }


def _loop_run(
    benchmark_id: str,
    center: tuple[float, float],
    side: float,
    orientation: str,
    loop_config: LoopConfig,
    open_config: OpenSystemConfig,
    cache: FixedPointCache,
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
    continuation = continue_path_with_branch_ids(benchmark=benchmark, path=path, config=loop_config)
    states = continuation["states"]
    branch_rhos = [cache.get(state, dephasing) for state in states]
    rho = branch_rhos[0].copy()
    operator = observable_operator(benchmark, states[0])
    actual_samples: list[float] = []
    branch_samples: list[float] = []
    coherence_samples: list[float] = []
    purity_samples: list[float] = []
    for state, branch_rho in zip(states, branch_rhos):
        rho = apply_local_open_step(rho, state=state, config=open_config, dephasing=dephasing)
        actual_samples.append(float(np.real(np.trace(rho @ operator))))
        branch_samples.append(float(np.real(np.trace(branch_rho @ operator))))
        coherence_samples.append(float(coherence_ratio(rho, state)))
        purity_samples.append(float(purity(rho)))

    if benchmark.primary_observable == "excess_circulation":
        response = float(np.mean(actual_samples) - np.mean(branch_samples))
    else:
        response = float(actual_samples[-1] - branch_samples[-1])

    mixed_holonomy = float(mixed_loop_holonomy_phase(branch_rhos))
    return {
        "center": [float(center[0]), float(center[1])],
        "side_length": float(side),
        "orientation": orientation,
        "dephasing": float(dephasing),
        "response": response,
        "mixed_holonomy_phase": mixed_holonomy,
        "avg_coherence_ratio": float(np.mean(coherence_samples)) if coherence_samples else 0.0,
        "final_coherence_ratio": float(coherence_samples[-1]) if coherence_samples else 0.0,
        "avg_purity": float(np.mean(purity_samples)) if purity_samples else 0.0,
        "switch_count": int(continuation["switch_count"]),
        "ambiguous_step_count": int(continuation["ambiguous_step_count"]),
        "unique_branch_ids": continuation["unique_branch_ids"],
    }


def _pair_row(ccw: dict, cw: dict) -> dict:
    trusted = (
        ccw["switch_count"] == 0
        and cw["switch_count"] == 0
        and ccw["ambiguous_step_count"] == 0
        and cw["ambiguous_step_count"] == 0
    )
    return {
        "center": ccw["center"],
        "side_length": ccw["side_length"],
        "dephasing": ccw["dephasing"],
        "trusted_pair": trusted,
        "pair_r4": not trusted,
        "orientation_gap": float(ccw["response"] - cw["response"]),
        "orientation_sum": float(ccw["response"] + cw["response"]),
        "mixed_holonomy_gap": float(ccw["mixed_holonomy_phase"] - cw["mixed_holonomy_phase"]),
        "mixed_holonomy_abs_mean": float(
            0.5 * (abs(ccw["mixed_holonomy_phase"]) + abs(cw["mixed_holonomy_phase"]))
        ),
        "avg_coherence_ratio_mean": float(0.5 * (ccw["avg_coherence_ratio"] + cw["avg_coherence_ratio"])),
        "avg_purity_mean": float(0.5 * (ccw["avg_purity"] + cw["avg_purity"])),
        "ccw": ccw,
        "cw": cw,
    }


def _fit_rows(rows: list[dict]) -> dict:
    trusted = [row for row in rows if row["trusted_pair"]]
    xs = np.asarray([row["mixed_holonomy_gap"] for row in trusted], dtype=float)
    ys = np.asarray([row["orientation_gap"] for row in trusted], dtype=float)
    return _fit_through_origin(xs, ys)


def phase10_payload(
    output_root: Path,
    phase10_config: Phase10Config | None = None,
    scan_config: ScanConfig | None = None,
    loop_config: LoopConfig | None = None,
    open_config: OpenSystemConfig | None = None,
) -> dict:
    p10 = phase10_config or Phase10Config()
    benchmark = get_benchmark(p10.benchmark_id)
    scan_cfg = scan_config or ScanConfig(mesh=p10.scan_mesh)
    loop_cfg = loop_config or LoopConfig(steps_per_segment=20)
    open_cfg = open_config or OpenSystemConfig(
        scan_mesh=p10.scan_mesh,
        dephasing_values=p10.dephasing_values,
        coherence_switch_floor=p10.coherence_switch_floor,
    )
    cache = FixedPointCache(open_cfg)

    benchmark_dir = output_root / benchmark.slug
    benchmark_dir.mkdir(parents=True, exist_ok=True)

    scan_levels = [
        _scan_level(benchmark.benchmark_id, scan_cfg, open_cfg, cache, gamma)
        for gamma in p10.dephasing_values
    ]

    loop_levels: list[dict] = []
    global_rows: list[dict] = []
    for gamma in p10.dephasing_values:
        rows: list[dict] = []
        for center in benchmark.default_loop_centers:
            for side in benchmark.default_loop_side_lengths:
                ccw = _loop_run(benchmark.benchmark_id, center, side, "ccw", loop_cfg, open_cfg, cache, gamma)
                cw = _loop_run(benchmark.benchmark_id, center, side, "cw", loop_cfg, open_cfg, cache, gamma)
                row = _pair_row(ccw, cw)
                rows.append(row)
                global_rows.append(row)
        loop_levels.append(
            {
                "dephasing": float(gamma),
                "pair_rows": rows,
                "fit_orientation_gap_vs_mixed_holonomy": _fit_rows(rows),
                "coherence_ratio_summary": summarize(row["avg_coherence_ratio_mean"] for row in rows),
                "purity_summary": summarize(row["avg_purity_mean"] for row in rows),
                "trusted_pair_count": int(sum(1 for row in rows if row["trusted_pair"])),
                "excluded_pair_count": int(sum(1 for row in rows if not row["trusted_pair"])),
            }
        )

    switch_gamma = None
    for level in loop_levels:
        mean_coh = level["coherence_ratio_summary"]["mean"]
        if mean_coh is not None and float(mean_coh) <= p10.coherence_switch_floor:
            switch_gamma = float(level["dephasing"])
            break
    if switch_gamma is None:
        switch_gamma = float(p10.dephasing_values[-1])

    selected_level = next(
        level for level in loop_levels if abs(float(level["dephasing"]) - switch_gamma) < 1e-9
    )
    patch_groups: dict[str, list[dict]] = {}
    for row in selected_level["pair_rows"]:
        center_key = f"({row['center'][0]:.2f},{row['center'][1]:.2f})"
        patch_groups.setdefault(center_key, []).append(row)
    patchwise_fits = {key: _fit_rows(rows) for key, rows in patch_groups.items()}
    global_fit = _fit_rows(selected_level["pair_rows"])

    payload = {
        "phase": "phase10_open_system_mixed_geometry",
        "benchmark": benchmark.benchmark_id,
        "slug": benchmark.slug,
        "description": (
            "Graph-local open-system lane plus genuine mixed-state holonomy / curvature diagnostics"
            " from an effective K-step noisy branch map."
        ),
        "open_system_config": {
            "dt": open_cfg.dt,
            "coherent_scale": open_cfg.coherent_scale,
            "edge_jump_scale": open_cfg.edge_jump_scale,
            "site_potential_scale": open_cfg.site_potential_scale,
            "depolarizing": open_cfg.depolarizing,
            "branch_steps": open_cfg.branch_steps,
            "fixed_point_max_iter": open_cfg.fixed_point_max_iter,
            "fixed_point_tol": open_cfg.fixed_point_tol,
        },
        "dephasing_values": [float(x) for x in p10.dephasing_values],
        "recommended_mixed_state_switch_gamma": float(switch_gamma),
        "scan_levels": scan_levels,
        "loop_levels": loop_levels,
        "patchwise_fit_at_switch_gamma": patchwise_fits,
        "global_fit_at_switch_gamma": global_fit,
        "notes": [
            "The noisy lane is now generated by a graph-local CPTP map built from the branch kernel"
            " and branch phase field, not by direct convex mixing with the target density.",
            "The mixed-state phase object is an Uhlmann-like holonomy computed from polar link unitaries"
            " of neighboring density amplitudes.",
            "Fits remain patchwise; the theory should not claim a single global susceptibility over the full"
            " control domain.",
        ],
    }
    (benchmark_dir / f"{benchmark.benchmark_id}_phase10.json").write_text(json.dumps(payload, indent=2))
    return payload


def _save_scatter_plot(
    path: Path,
    xs: np.ndarray,
    ys: np.ndarray,
    xlabel: str,
    ylabel: str,
    title: str,
    fit: dict[str, float | int | None],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(6.0, 4.2))
    plt.scatter(xs, ys)
    if fit.get("slope") is not None:
        x_line = np.linspace(float(np.min(xs)), float(np.max(xs)), 200) if xs.size else np.asarray([0.0, 1.0])
        plt.plot(x_line, float(fit["slope"]) * x_line)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _save_line_plot(path: Path, xs: np.ndarray, ys: np.ndarray, xlabel: str, ylabel: str, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(6.0, 4.2))
    plt.plot(xs, ys, marker="o")
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def phase10_report(output_root: Path, payload: dict) -> dict[str, Path]:
    benchmark_slug = payload["slug"]
    project_root = output_root.parents[1]
    plots_dir = project_root / "05_reports" / "plots" / "phase10_open_system" / benchmark_slug
    reports_dir = project_root / "05_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    switch_gamma = float(payload["recommended_mixed_state_switch_gamma"])
    level = next(
        level for level in payload["loop_levels"] if abs(float(level["dephasing"]) - switch_gamma) < 1e-9
    )
    trusted_rows = [row for row in level["pair_rows"] if row["trusted_pair"]]
    xs = np.asarray([row["mixed_holonomy_gap"] for row in trusted_rows], dtype=float)
    ys = np.asarray([row["orientation_gap"] for row in trusted_rows], dtype=float)
    scatter_path = plots_dir / "response_vs_mixed_holonomy.png"
    _save_scatter_plot(
        scatter_path,
        xs,
        ys,
        xlabel="mixed holonomy gap",
        ylabel="orientation gap",
        title=f"Benchmark C response vs mixed holonomy (γ={switch_gamma:.2f})",
        fit=payload["global_fit_at_switch_gamma"],
    )

    scan_xs = np.asarray([level["dephasing"] for level in payload["scan_levels"]], dtype=float)
    scan_ys = np.asarray([level["mean_abs_mixed_curvature"] for level in payload["scan_levels"]], dtype=float)
    curvature_path = plots_dir / "mixed_curvature_scale_vs_dephasing.png"
    _save_line_plot(
        curvature_path,
        scan_xs,
        scan_ys,
        xlabel="dephasing γ",
        ylabel="mean |mixed curvature|",
        title="Benchmark C mixed curvature scale vs dephasing",
    )

    md_path = reports_dir / "CWT-CGT_Phase_10_Report.md"
    patch_lines = []
    for center_key, fit in payload["patchwise_fit_at_switch_gamma"].items():
        patch_lines.append(
            f"- center {center_key}: slope={fit['slope']}, R²={fit['r2']}, count={fit['count']}"
        )
    curv_by_gamma = [format(level["mean_abs_mixed_curvature"], ".3e") for level in payload["scan_levels"]]
    md_text = (
        "# CWT-CGT Phase 10 Report\n"
        "\n"
        "## What Phase 10 adds\n"
        "\n"
        "Phase 10 replaces the earlier operational noisy surrogate with a **graph-local open-system CPTP"
        " lane** and adds a genuine **mixed-state holonomy / curvature object**.\n"
        "\n"
        "The open-system step is built from:\n"
        "- a branch-local coherent Hamiltonian derived from symmetric edge couplings and branch phases,\n"
        "- local directed jump operators derived from the graph kernel,\n"
        "- sitewise dephasing operators,\n"
        "- and a small depolarizing background for numerical stability.\n"
        "\n"
        "The mixed-state geometric object is an **Uhlmann-like holonomy** formed from polar link unitaries"
        " between neighboring density amplitudes. Bures metric traces remain the metric side of the"
        " mixed-state lane.\n"
        "\n"
        "## Current benchmark-C result\n"
        "\n"
        f"Recommended mixed-state switch: **γ ≈ {switch_gamma:.2f}**.\n"
        "\n"
        "Global fit at the switch point:\n"
        f"- slope = {payload['global_fit_at_switch_gamma']['slope']}\n"
        f"- R² = {payload['global_fit_at_switch_gamma']['r2']}\n"
        f"- trusted pair count = {payload['global_fit_at_switch_gamma']['count']}\n"
        "\n"
        "Patchwise fits at the switch point:\n"
        + "\n".join(patch_lines)
        + "\n"
        "\n"
        f"Coherence trend:\n"
        f"- γ grid = {payload['dephasing_values']}\n"
        f"- mean |mixed curvature| by γ = {curv_by_gamma}\n"
        "\n"
        "## Interpretation\n"
        "\n"
        "Phase 10 supports the stronger claim that the noisy lane is now tied to a **graph-local open-system"
        " rule** rather than direct target interpolation. It also upgrades the mixed-state phase object from"
        " a placeholder to a real holonomy diagnostic.\n"
        "\n"
        "The fit remains patchwise. That means the theory should continue to state the noisy law as a local"
        " susceptibility law rather than as a single universal global coefficient.\n"
    )
    md_path.write_text(md_text, encoding='utf-8')
    return {
        "report": md_path,
        "scatter_plot": scatter_path,
        "curvature_plot": curvature_path,
    }
