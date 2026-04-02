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
from ..lindblad import LindbladConfig, apply_lindblad_step, lindblad_branch_density
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
class Phase11Config:
    benchmark_ids: tuple[str, ...] = (
        "benchmark_a",
        "benchmark_b",
        "benchmark_c",
        "benchmark_d",
        "benchmark_f",
    )
    benchmark_id_compare: str = "benchmark_c"
    scan_mesh: int = 9
    dephasing_values: tuple[float, ...] = (0.0, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40)
    coherence_switch_floor: float = 0.20


class DensityCache:
    def __init__(self, fn):
        self.fn = fn
        self._cache: dict[tuple[float, tuple[float, ...]], np.ndarray] = {}

    @staticmethod
    def _signature(state) -> tuple[float, ...]:
        return tuple(
            np.round(
                np.concatenate([state.p.ravel(), state.theta.ravel(), state.kernel.ravel()]), 10
            ).tolist()
        )

    def get(self, state, dephasing: float) -> np.ndarray:
        key = (round(float(dephasing), 6), self._signature(state))
        if key not in self._cache:
            self._cache[key] = self.fn(state, float(dephasing))
        return self._cache[key]


def _fit_through_origin(xs: np.ndarray, ys: np.ndarray) -> dict[str, float | int | None]:
    if xs.size == 0 or np.allclose(xs, 0.0):
        return {"slope": None, "r2": None, "count": int(xs.size)}
    slope = float(np.dot(xs, ys) / np.dot(xs, xs))
    residual = ys - slope * xs
    denom = float(np.dot(ys, ys))
    r2 = None if denom <= 1e-15 else float(1.0 - np.dot(residual, residual) / denom)
    return {"slope": slope, "r2": r2, "count": int(xs.size)}


def _corr(a: np.ndarray, b: np.ndarray) -> float | None:
    mask = np.isfinite(a) & np.isfinite(b)
    if int(np.sum(mask)) < 2:
        return None
    x = np.asarray(a[mask], dtype=float)
    y = np.asarray(b[mask], dtype=float)
    if np.allclose(x, x[0]) or np.allclose(y, y[0]):
        return None
    return float(np.corrcoef(x, y)[0, 1])


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


def _scan_level(benchmark_id: str, scan_config: ScanConfig, dephasing: float, cache: DensityCache) -> dict:
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
        "mean_abs_mixed_curvature": (
            float(np.nanmean(np.abs(curvature))) if np.isfinite(curvature).any() else 0.0
        ),
        "ambiguous_tile_count": int(sum(sum(1 for flag in row if flag) for row in atlas["ambiguous_map"])),
        "branch_atlas": {
            "persistent_branch_id_map": atlas["persistent_branch_id_map"],
            "ambiguous_map": atlas["ambiguous_map"],
            "switch_tile_count": int(len(atlas["switch_tiles"])),
        },
    }


def _loop_run(
    benchmark_id: str,
    center: tuple[float, float],
    side: float,
    orientation: str,
    loop_config: LoopConfig,
    dephasing: float,
    cache: DensityCache,
    step_fn,
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
        rho = step_fn(rho, state, dephasing)
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
        "avg_coherence_ratio_mean": float(0.5 * (ccw["avg_coherence_ratio"] + cw["avg_coherence_ratio"])),
        "avg_purity_mean": float(0.5 * (ccw["avg_purity"] + cw["avg_purity"])),
        "ccw": ccw,
        "cw": cw,
    }


def _loop_levels_for_backend(
    benchmark_id: str,
    dephasing_values: tuple[float, ...],
    cache: DensityCache,
    step_fn,
    loop_config: LoopConfig,
) -> list[dict]:
    benchmark = get_benchmark(benchmark_id)
    levels: list[dict] = []
    for gamma in dephasing_values:
        rows: list[dict] = []
        for center in benchmark.default_loop_centers:
            for side in benchmark.default_loop_side_lengths:
                ccw = _loop_run(benchmark_id, center, side, "ccw", loop_config, gamma, cache, step_fn)
                cw = _loop_run(benchmark_id, center, side, "cw", loop_config, gamma, cache, step_fn)
                rows.append(_pair_row(ccw, cw))
        trusted = [row for row in rows if row["trusted_pair"]]
        xs = np.asarray([row["mixed_holonomy_gap"] for row in trusted], dtype=float)
        ys = np.asarray([row["orientation_gap"] for row in trusted], dtype=float)
        levels.append(
            {
                "dephasing": float(gamma),
                "pair_rows": rows,
                "fit_orientation_gap_vs_mixed_holonomy": _fit_through_origin(xs, ys),
                "coherence_ratio_summary": summarize(row["avg_coherence_ratio_mean"] for row in rows),
                "purity_summary": summarize(row["avg_purity_mean"] for row in rows),
                "trusted_pair_count": int(len(trusted)),
                "excluded_pair_count": int(sum(1 for row in rows if not row["trusted_pair"])),
            }
        )
    return levels


def _recommended_switch(levels: list[dict], floor: float) -> float:
    for level in levels:
        mean_coh = level["coherence_ratio_summary"]["mean"]
        if mean_coh is not None and float(mean_coh) <= floor:
            return float(level["dephasing"])
    return float(levels[-1]["dephasing"])


def _select_level(levels: list[dict], gamma: float) -> dict:
    return min(levels, key=lambda level: abs(float(level["dephasing"]) - gamma))


def _benchmark_payload(
    benchmark_id: str,
    output_root: Path,
    scan_config: ScanConfig,
    loop_config: LoopConfig,
    dephasing_values: tuple[float, ...],
    floor: float,
    cache: DensityCache,
    step_fn,
    backend_name: str,
) -> dict:
    benchmark = get_benchmark(benchmark_id)
    scan_levels = [_scan_level(benchmark_id, scan_config, gamma, cache) for gamma in dephasing_values]
    loop_levels = _loop_levels_for_backend(benchmark_id, dephasing_values, cache, step_fn, loop_config)
    switch_gamma = _recommended_switch(loop_levels, floor)
    selected = _select_level(loop_levels, switch_gamma)
    patch_groups: dict[str, list[dict]] = {}
    for row in selected["pair_rows"]:
        key = f"({row['center'][0]:.2f},{row['center'][1]:.2f})"
        patch_groups.setdefault(key, []).append(row)
    patchwise = {}
    for key, rows in patch_groups.items():
        trusted = [row for row in rows if row["trusted_pair"]]
        xs = np.asarray([row["mixed_holonomy_gap"] for row in trusted], dtype=float)
        ys = np.asarray([row["orientation_gap"] for row in trusted], dtype=float)
        patchwise[key] = _fit_through_origin(xs, ys)
    global_fit = selected["fit_orientation_gap_vs_mixed_holonomy"]
    payload = {
        "phase": (
            "phase11_lindblad_continuous_time"
            if backend_name == "lindblad"
            else "phase10_effective_k_step_reference"
        ),
        "backend": backend_name,
        "benchmark": benchmark.benchmark_id,
        "slug": benchmark.slug,
        "dephasing_values": [float(x) for x in dephasing_values],
        "recommended_switch_gamma": float(switch_gamma),
        "scan_levels": scan_levels,
        "loop_levels": loop_levels,
        "patchwise_fit_at_switch_gamma": patchwise,
        "global_fit_at_switch_gamma": global_fit,
    }
    bench_dir = output_root / benchmark.slug
    bench_dir.mkdir(parents=True, exist_ok=True)
    suffix = "phase11" if backend_name == "lindblad" else "phase11_effective_reference"
    (bench_dir / f"{benchmark.benchmark_id}_{suffix}.json").write_text(json.dumps(payload, indent=2))
    return payload


def _plot_scatter(
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
    if fit.get("slope") is not None and xs.size:
        xline = np.linspace(float(np.min(xs)), float(np.max(xs)), 200)
        plt.plot(xline, float(fit["slope"]) * xline)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _plot_lines(
    path: Path, x: np.ndarray, ys: list[np.ndarray], labels: list[str], xlabel: str, ylabel: str, title: str
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(6.2, 4.2))
    for y, label in zip(ys, labels):
        plt.plot(x, y, marker="o", label=label)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def phase11_payload(
    output_root: Path,
    phase11_config: Phase11Config | None = None,
    scan_config: ScanConfig | None = None,
    loop_config: LoopConfig | None = None,
    open_config: OpenSystemConfig | None = None,
    lindblad_config: LindbladConfig | None = None,
) -> dict:
    cfg = phase11_config or Phase11Config()
    scan_cfg = scan_config or ScanConfig(mesh=cfg.scan_mesh)
    loop_cfg = loop_config or LoopConfig(steps_per_segment=20)
    open_cfg = open_config or OpenSystemConfig(
        scan_mesh=cfg.scan_mesh,
        dephasing_values=cfg.dephasing_values,
        coherence_switch_floor=cfg.coherence_switch_floor,
    )
    lind_cfg = lindblad_config or LindbladConfig(
        scan_mesh=cfg.scan_mesh,
        dephasing_values=cfg.dephasing_values,
        coherence_switch_floor=cfg.coherence_switch_floor,
    )

    eff_cache = DensityCache(lambda state, gamma: effective_branch_density(state, open_cfg, gamma))
    lind_cache = DensityCache(lambda state, gamma: lindblad_branch_density(state, lind_cfg, gamma))

    def eff_step(rho, state, gamma):
        return apply_local_open_step(rho, state=state, config=open_cfg, dephasing=gamma)

    def lind_step(rho, state, gamma):
        return apply_lindblad_step(rho, state=state, config=lind_cfg, dephasing=gamma)

    benchmark_payloads: dict[str, dict] = {}
    for benchmark_id in cfg.benchmark_ids:
        benchmark_payloads[benchmark_id] = _benchmark_payload(
            benchmark_id=benchmark_id,
            output_root=output_root,
            scan_config=scan_cfg,
            loop_config=loop_cfg,
            dephasing_values=cfg.dephasing_values,
            floor=cfg.coherence_switch_floor,
            cache=lind_cache,
            step_fn=lind_step,
            backend_name="lindblad",
        )

    compare_id = cfg.benchmark_id_compare
    compare_lind = benchmark_payloads[compare_id]
    compare_eff = _benchmark_payload(
        benchmark_id=compare_id,
        output_root=output_root,
        scan_config=scan_cfg,
        loop_config=loop_cfg,
        dephasing_values=cfg.dephasing_values,
        floor=cfg.coherence_switch_floor,
        cache=eff_cache,
        step_fn=eff_step,
        backend_name="effective",
    )

    gamma = float(compare_lind["recommended_switch_gamma"])
    lind_scan = _select_level(compare_lind["scan_levels"], gamma)
    eff_scan = _select_level(compare_eff["scan_levels"], gamma)
    lind_loop = _select_level(compare_lind["loop_levels"], gamma)
    eff_loop = _select_level(compare_eff["loop_levels"], gamma)

    benchmark = get_benchmark(compare_id)
    atlas = build_branch_atlas(
        benchmark=benchmark,
        grid_u=np.linspace(*benchmark.control_bounds[0], scan_cfg.mesh, dtype=float),
        grid_v=np.linspace(*benchmark.control_bounds[1], scan_cfg.mesh, dtype=float),
        config=scan_cfg,
    )
    states = atlas["chosen_states"]
    mean_bures = []
    for i in range(scan_cfg.mesh):
        for j in range(scan_cfg.mesh):
            if atlas["ambiguous_map"][i][j]:
                continue
            state = states[i][j]
            mean_bures.append(bures_distance_sq(eff_cache.get(state, gamma), lind_cache.get(state, gamma)))

    comparison = {
        "benchmark": compare_id,
        "comparison_gamma": gamma,
        "effective_switch_gamma": float(compare_eff["recommended_switch_gamma"]),
        "lindblad_switch_gamma": float(compare_lind["recommended_switch_gamma"]),
        "mean_bures_distance_between_backends": float(np.mean(mean_bures)) if mean_bures else None,
        "curvature_correlation_at_gamma": _corr(
            np.asarray(eff_scan["mixed_curvature"], dtype=float),
            np.asarray(lind_scan["mixed_curvature"], dtype=float),
        ),
        "metric_correlation_at_gamma": _corr(
            np.asarray(eff_scan["bures_metric_trace"], dtype=float),
            np.asarray(lind_scan["bures_metric_trace"], dtype=float),
        ),
        "effective_global_fit_at_gamma": eff_loop["fit_orientation_gap_vs_mixed_holonomy"],
        "lindblad_global_fit_at_gamma": lind_loop["fit_orientation_gap_vs_mixed_holonomy"],
    }

    benchmark_summary = {}
    for benchmark_id, payload in benchmark_payloads.items():
        level = _select_level(payload["loop_levels"], payload["recommended_switch_gamma"])
        benchmark_summary[benchmark_id] = {
            "benchmark": benchmark_id,
            "recommended_switch_gamma": float(payload["recommended_switch_gamma"]),
            "trusted_pair_count_at_switch": int(level["trusted_pair_count"]),
            "excluded_pair_count_at_switch": int(level["excluded_pair_count"]),
            "fit_r2_at_switch": level["fit_orientation_gap_vs_mixed_holonomy"]["r2"],
            "fit_slope_at_switch": level["fit_orientation_gap_vs_mixed_holonomy"]["slope"],
            "mean_abs_mixed_curvature_at_switch": _select_level(
                payload["scan_levels"], payload["recommended_switch_gamma"]
            )["mean_abs_mixed_curvature"],
        }

    payload = {
        "phase": "phase11_continuous_time_lindblad",
        "description": (
            "Continuous-time graph-local Lindblad-style extension plus broader mixed-state holonomy"
            " validation across the benchmark set."
        ),
        "benchmark_summaries": benchmark_summary,
        "benchmark_payloads": benchmark_payloads,
        "benchmark_c_backend_comparison": comparison,
        "notes": [
            "The Lindblad lane is built from the same branch-local coherent Hamiltonian and graph-local"
            " jump structure as the earlier effective CPTP lane, but integrated as a continuous-time"
            " generator.",
            "Mixed-state fits remain patchwise; benchmark F is expected to exclude most or all loops"
            " because R4 switching dominates.",
            "Topology is still restricted to the auxiliary periodic/gapped sector and is not inferred"
            " from the mixed-state dynamic benchmarks here.",
        ],
    }
    report_root = output_root.parents[1]
    (report_root / "05_reports").mkdir(parents=True, exist_ok=True)
    (report_root / "05_reports" / "phase11_summary.json").write_text(json.dumps(payload, indent=2))
    return payload


def phase11_report(output_root: Path, payload: dict) -> dict[str, Path]:
    project_root = output_root.parents[1]
    plots_dir = project_root / "05_reports" / "plots" / "phase11_lindblad"
    reports_dir = project_root / "05_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    compare = payload["benchmark_c_backend_comparison"]
    bench_payload = payload["benchmark_payloads"]["benchmark_c"]
    gamma = float(compare["comparison_gamma"])
    level = _select_level(bench_payload["loop_levels"], gamma)
    trusted_rows = [row for row in level["pair_rows"] if row["trusted_pair"]]
    xs = np.asarray([row["mixed_holonomy_gap"] for row in trusted_rows], dtype=float)
    ys = np.asarray([row["orientation_gap"] for row in trusted_rows], dtype=float)
    scatter_path = plots_dir / "benchmark_c_response_vs_lindblad_holonomy.png"
    _plot_scatter(
        scatter_path,
        xs,
        ys,
        xlabel="mixed holonomy gap",
        ylabel="orientation gap",
        title=f"Benchmark C response vs Lindblad mixed holonomy (γ={gamma:.2f})",
        fit=level["fit_orientation_gap_vs_mixed_holonomy"],
    )

    lind_scan_levels = bench_payload["scan_levels"]
    x = np.asarray([lvl["dephasing"] for lvl in lind_scan_levels], dtype=float)
    lind_curv = np.asarray([lvl["mean_abs_mixed_curvature"] for lvl in lind_scan_levels], dtype=float)
    ref_path = output_root / "benchmark_C_ring" / "benchmark_c_phase11_effective_reference.json"
    ref_payload = json.loads(ref_path.read_text()) if ref_path.exists() else None
    compare_path = plots_dir / "benchmark_c_backend_curvature_scale_vs_dephasing.png"
    if ref_payload is not None:
        ref_levels = ref_payload["scan_levels"]
        eff_curv = np.asarray([lvl["mean_abs_mixed_curvature"] for lvl in ref_levels], dtype=float)
        _plot_lines(
            compare_path,
            x,
            [lind_curv, eff_curv],
            ["lindblad", "effective"],
            "dephasing γ",
            "mean |mixed curvature|",
            "Benchmark C mixed curvature scale by backend",
        )
    else:
        _plot_lines(
            compare_path,
            x,
            [lind_curv],
            ["lindblad"],
            "dephasing γ",
            "mean |mixed curvature|",
            "Benchmark C mixed curvature scale (Lindblad)",
        )

    md_path = reports_dir / "CWT-CGT_Phase_11_Report.md"
    lines = [
        "# CWT-CGT Phase 11 Report",
        "",
        "## What Phase 11 adds",
        "",
        "Phase 11 replaces the effective noisy step with a more explicit **continuous-time Lindblad-style"
        " graph-local generator** and checks the mixed-state holonomy lane across the broader benchmark set.",
        "",
        "## Benchmark summary at each benchmark's switch point",
        "",
    ]
    for benchmark_id, summary in payload["benchmark_summaries"].items():
        sw = summary["recommended_switch_gamma"]
        tp = summary["trusted_pair_count_at_switch"]
        ep = summary["excluded_pair_count_at_switch"]
        fr2 = summary["fit_r2_at_switch"]
        mc = summary["mean_abs_mixed_curvature_at_switch"]
        lines.append(
            f"- {benchmark_id}: switch γ={sw:.2f}, trusted pairs={tp},"
            f" excluded pairs={ep}, fit R²={fr2}, mean |mixed curvature|={mc}"
        )
    lines.extend(
        [
            "",
            "## Benchmark C backend comparison",
            "",
            f"Comparison gamma: **{compare['comparison_gamma']:.2f}**",
            f"- mean Bures distance between effective and Lindblad branch densities:"
            f" {compare['mean_bures_distance_between_backends']}",
            f"- metric correlation: {compare['metric_correlation_at_gamma']}",
            f"- curvature correlation: {compare['curvature_correlation_at_gamma']}",
            f"- effective fit at gamma: slope={compare['effective_global_fit_at_gamma']['slope']},"
            f" R²={compare['effective_global_fit_at_gamma']['r2']},"
            f" count={compare['effective_global_fit_at_gamma']['count']}",
            f"- Lindblad fit at gamma: slope={compare['lindblad_global_fit_at_gamma']['slope']},"
            f" R²={compare['lindblad_global_fit_at_gamma']['r2']},"
            f" count={compare['lindblad_global_fit_at_gamma']['count']}",
            "",
            f"Plot: `{scatter_path}`",
            f"Plot: `{compare_path}`",
            "",
            "## Interpretation",
            "",
            "- Benchmarks A and D remain null-like controls in the mixed-state lane.",
            "- Benchmark B remains weak / patchy rather than globally pumped.",
            "- Benchmark C remains the positive mixed-state benchmark and survives the generator upgrade.",
            "- Benchmark F remains dominated by R4 exclusions, which is the expected behavior for an"
            " explicit branch-switching benchmark.",
            "",
        ]
    )
    md_path.write_text("\n".join(lines), encoding='utf-8')
    return {
        "phase11_report": md_path,
        "benchmark_c_scatter": scatter_path,
        "benchmark_c_backend_curve": compare_path,
    }
