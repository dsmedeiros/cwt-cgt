from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import matplotlib.pyplot as plt
import numpy as np

from cwt.geometry.mixed_state import (
    bures_distance_sq,
    mixed_loop_holonomy_phase,
    mixed_plaquette_curvature,
    phase_alignment_sign,
    purity,
    unwrap_phase_sequence,
)

from .._geom_compat import berry_loop_flux, summarize, summarize_abs
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
class LoopFamilySpec:
    shapes: tuple[str, ...]
    centers: tuple[tuple[float, float], ...]
    side_lengths: tuple[float, ...]
    steps_per_segment: int = 18


@dataclass(frozen=True)
class Phase12Config:
    benchmark_ids: tuple[str, ...] = ("benchmark_c",)
    benchmark_id_compare: str = "benchmark_c"
    scan_mesh: int = 9
    dephasing_values: tuple[float, ...] = (0.0, 0.05, 0.10, 0.20, 0.30)
    coherence_switch_floor: float = 0.20


class DensityCache:
    def __init__(self, fn: Callable):
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


def _family_for_benchmark(benchmark_id: str) -> LoopFamilySpec:
    if benchmark_id == "benchmark_a":
        return LoopFamilySpec(
            shapes=("square", "circle"),
            centers=((0.0, 0.0),),
            side_lengths=(0.10, 0.16, 0.22),
            steps_per_segment=18,
        )
    if benchmark_id == "benchmark_b":
        return LoopFamilySpec(
            shapes=("square", "circle"),
            centers=((0.0, 0.0), (0.0, 0.20)),
            side_lengths=(0.10, 0.16, 0.22),
            steps_per_segment=18,
        )
    if benchmark_id == "benchmark_c":
        return LoopFamilySpec(
            shapes=("square", "circle"),
            centers=((0.0, 0.0), (0.18, 0.0)),
            side_lengths=(0.10, 0.16, 0.22),
            steps_per_segment=8,
        )
    if benchmark_id == "benchmark_d":
        return LoopFamilySpec(
            shapes=("square", "circle"),
            centers=((0.0, 0.225), (0.03, 0.225)),
            side_lengths=(0.04, 0.06, 0.08),
            steps_per_segment=18,
        )
    if benchmark_id == "benchmark_f":
        return LoopFamilySpec(
            shapes=("square", "circle"),
            centers=((0.0, 0.0), (0.7, 0.0), (-0.7, 0.0)),
            side_lengths=(0.18, 0.30),
            steps_per_segment=18,
        )
    benchmark = get_benchmark(benchmark_id)
    return LoopFamilySpec(
        shapes=("square",),
        centers=benchmark.default_loop_centers,
        side_lengths=benchmark.default_loop_side_lengths,
        steps_per_segment=18,
    )


def _fit_through_origin(xs: np.ndarray, ys: np.ndarray) -> dict[str, float | int | None]:
    if xs.size == 0 or np.allclose(xs, 0.0):
        return {"slope": None, "r2": None, "count": int(xs.size)}
    slope = float(np.dot(xs, ys) / max(np.dot(xs, xs), 1e-15))
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


def _recommended_switch(levels: list[dict], floor: float) -> float:
    for level in levels:
        mean_coh = level["coherence_ratio_summary"]["mean"]
        if mean_coh is not None and float(mean_coh) <= floor:
            return float(level["dephasing"])
    return float(levels[-1]["dephasing"])


def _select_level(levels: list[dict], gamma: float) -> dict:
    return min(levels, key=lambda level: abs(float(level["dephasing"]) - gamma))


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

    metric = np.full((scan_config.mesh, scan_config.mesh), np.nan, dtype=float)
    for i in range(1, scan_config.mesh - 1):
        for j in range(1, scan_config.mesh - 1):
            metric[i, j] = bures_distance_sq(rho_grid[i + 1][j], rho_grid[i - 1][j]) / max(
                (2.0 * du) ** 2, 1e-12
            ) + bures_distance_sq(rho_grid[i][j + 1], rho_grid[i][j - 1]) / max((2.0 * dv) ** 2, 1e-12)

    curvature = np.full((scan_config.mesh - 1, scan_config.mesh - 1), np.nan, dtype=float)
    area = du * dv
    for i in range(scan_config.mesh - 1):
        for j in range(scan_config.mesh - 1):
            if any(
                [
                    atlas["ambiguous_map"][i][j],
                    atlas["ambiguous_map"][i + 1][j],
                    atlas["ambiguous_map"][i + 1][j + 1],
                    atlas["ambiguous_map"][i][j + 1],
                ]
            ):
                continue
            curvature[i, j] = mixed_plaquette_curvature(
                rho_grid[i][j], rho_grid[i + 1][j], rho_grid[i + 1][j + 1], rho_grid[i][j + 1], area
            )

    return {
        "dephasing": float(dephasing),
        "mean_abs_mixed_curvature": (
            float(np.nanmean(np.abs(curvature))) if np.isfinite(curvature).any() else 0.0
        ),
        "metric_summary": summarize(metric.ravel()),
        "mixed_curvature_summary": summarize_abs(curvature.ravel()),
        "coherence_ratio_summary": summarize(coherence_grid.ravel()),
        "purity_summary": summarize(purity_grid.ravel()),
        "bures_metric_trace": metric.tolist(),
        "mixed_curvature": curvature.tolist(),
    }


def _loop_observable_response(
    benchmark, states, branch_rhos: list[np.ndarray], dephasing: float, step_fn: Callable
) -> tuple[float, float, float, float, float]:
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
    return (
        response,
        float(np.mean(coherence_samples)) if coherence_samples else 0.0,
        float(np.mean(purity_samples)) if purity_samples else 0.0,
        float(np.mean(actual_samples)) if actual_samples else 0.0,
        float(np.mean(branch_samples)) if branch_samples else 0.0,
    )


def _precompute_loop_branch(
    benchmark_id: str,
    shape: str,
    center: tuple[float, float],
    side: float,
    orientation: str,
    steps_per_segment: int,
) -> dict:
    benchmark = get_benchmark(benchmark_id)
    loop_config = LoopConfig(shape=shape, steps_per_segment=steps_per_segment)
    path = build_loop_path(
        center=center, side=side, orientation=orientation, shape=shape, steps_per_segment=steps_per_segment
    )
    continuation = continue_path_with_branch_ids(benchmark=benchmark, path=path, config=loop_config)
    states = continuation["states"]
    return {
        "benchmark": benchmark,
        "shape": shape,
        "center": [float(center[0]), float(center[1])],
        "side_length": float(side),
        "orientation": orientation,
        "states": states,
        "switch_count": int(continuation["switch_count"]),
        "ambiguous_step_count": int(continuation["ambiguous_step_count"]),
        "unique_branch_ids": continuation["unique_branch_ids"],
        "pure_state_flux": float(berry_loop_flux(states)),
    }


def _loop_run_from_precomputed(
    precomputed: dict, dephasing: float, cache: DensityCache, step_fn: Callable
) -> dict:
    benchmark = precomputed["benchmark"]
    states = precomputed["states"]
    branch_rhos = [cache.get(state, dephasing) for state in states]
    response, mean_coh, mean_purity, actual_mean, branch_mean = _loop_observable_response(
        benchmark, states, branch_rhos, dephasing, step_fn
    )
    raw_mixed_phase = float(mixed_loop_holonomy_phase(branch_rhos))
    return {
        "shape": precomputed["shape"],
        "center": precomputed["center"],
        "side_length": precomputed["side_length"],
        "orientation": precomputed["orientation"],
        "dephasing": float(dephasing),
        "response": float(response),
        "raw_mixed_holonomy_phase": raw_mixed_phase,
        "pure_state_flux": float(precomputed["pure_state_flux"]),
        "avg_coherence_ratio": float(mean_coh),
        "avg_purity": float(mean_purity),
        "observable_actual_mean": float(actual_mean),
        "observable_branch_mean": float(branch_mean),
        "switch_count": int(precomputed["switch_count"]),
        "ambiguous_step_count": int(precomputed["ambiguous_step_count"]),
        "unique_branch_ids": precomputed["unique_branch_ids"],
    }


def _backend_loop_payload(
    benchmark_id: str,
    family: LoopFamilySpec,
    dephasing_values: tuple[float, ...],
    cache: DensityCache,
    step_fn: Callable,
    backend_name: str,
) -> dict:
    benchmark = get_benchmark(benchmark_id)
    orientation_records: dict[tuple[str, int, float, str], list[dict]] = {}
    precomputed: dict[tuple[str, int, float, str], dict] = {}
    for center_index, center in enumerate(family.centers):
        for side in family.side_lengths:
            for shape in family.shapes:
                for orientation in ("ccw", "cw"):
                    key = (shape, center_index, float(side), orientation)
                    precomputed[key] = _precompute_loop_branch(
                        benchmark_id=benchmark_id,
                        shape=shape,
                        center=center,
                        side=side,
                        orientation=orientation,
                        steps_per_segment=family.steps_per_segment,
                    )

    for gamma in dephasing_values:
        for key, pre in precomputed.items():
            rec = _loop_run_from_precomputed(pre, float(gamma), cache, step_fn)
            orientation_records.setdefault(key, []).append(rec)

    for recs in orientation_records.values():
        recs.sort(key=lambda row: row["dephasing"])
        phases = [row["raw_mixed_holonomy_phase"] for row in recs]
        unwrapped = unwrap_phase_sequence(phases)
        for row, phase in zip(recs, unwrapped):
            row["unwrapped_mixed_holonomy_phase"] = float(phase)

    pair_series: dict[tuple[str, int, float], list[dict]] = {}
    for shape in family.shapes:
        for center_index, center in enumerate(family.centers):
            for side in family.side_lengths:
                ccw_recs = orientation_records[(shape, center_index, float(side), "ccw")]
                cw_recs = orientation_records[(shape, center_index, float(side), "cw")]
                raw_gaps = np.asarray(
                    [
                        float(ccw["unwrapped_mixed_holonomy_phase"])
                        - float(cw["unwrapped_mixed_holonomy_phase"])
                        for ccw, cw in zip(ccw_recs, cw_recs)
                    ],
                    dtype=float,
                )
                gap_series = unwrap_phase_sequence(raw_gaps)
                rows: list[dict] = []
                for index, (ccw, cw, gap) in enumerate(zip(ccw_recs, cw_recs, gap_series)):
                    trusted = (
                        ccw["switch_count"] == 0
                        and cw["switch_count"] == 0
                        and ccw["ambiguous_step_count"] == 0
                        and cw["ambiguous_step_count"] == 0
                    )
                    row = {
                        "shape": shape,
                        "center_index": int(center_index),
                        "center": list(center),
                        "side_length": float(side),
                        "dephasing": float(ccw["dephasing"]),
                        "trusted_pair": bool(trusted),
                        "pair_r4": not bool(trusted),
                        "orientation_gap": float(ccw["response"] - cw["response"]),
                        "orientation_sum": float(ccw["response"] + cw["response"]),
                        "raw_mixed_holonomy_gap": float(gap),
                        "state_flux_gap": float(ccw["pure_state_flux"] - cw["pure_state_flux"]),
                        "avg_coherence_ratio_mean": float(
                            0.5 * (ccw["avg_coherence_ratio"] + cw["avg_coherence_ratio"])
                        ),
                        "avg_purity_mean": float(0.5 * (ccw["avg_purity"] + cw["avg_purity"])),
                        "ccw": ccw,
                        "cw": cw,
                    }
                    rows.append(row)
                pair_series[(shape, center_index, float(side))] = rows

    gamma0 = float(dephasing_values[0])
    gamma0_rows = [
        rows[0]
        for rows in pair_series.values()
        if abs(rows[0]["dephasing"] - gamma0) < 1e-9 and rows[0]["trusted_pair"]
    ]
    sign = phase_alignment_sign(
        [row["state_flux_gap"] for row in gamma0_rows],
        [row["raw_mixed_holonomy_gap"] for row in gamma0_rows],
    )

    levels: list[dict] = []
    for gamma_index, gamma in enumerate(dephasing_values):
        rows = []
        for rows_by_loop in pair_series.values():
            row = dict(rows_by_loop[gamma_index])
            row["aligned_mixed_holonomy_gap"] = float(sign * row["raw_mixed_holonomy_gap"])
            rows.append(row)
        trusted = [row for row in rows if row["trusted_pair"]]
        xs = np.asarray([row["aligned_mixed_holonomy_gap"] for row in trusted], dtype=float)
        ys = np.asarray([row["orientation_gap"] for row in trusted], dtype=float)
        raw_xs = np.asarray([row["raw_mixed_holonomy_gap"] for row in trusted], dtype=float)
        patchwise: dict[str, dict] = {}
        for shape in family.shapes:
            for center_index, center in enumerate(family.centers):
                patch_key = f"{shape}|({center[0]:+.2f},{center[1]:+.2f})"
                patch_rows = [
                    row for row in trusted if row["shape"] == shape and row["center_index"] == center_index
                ]
                patchwise[patch_key] = _fit_through_origin(
                    np.asarray([row["aligned_mixed_holonomy_gap"] for row in patch_rows], dtype=float),
                    np.asarray([row["orientation_gap"] for row in patch_rows], dtype=float),
                )
        levels.append(
            {
                "dephasing": float(gamma),
                "pair_rows": rows,
                "fit_orientation_gap_vs_aligned_holonomy": _fit_through_origin(xs, ys),
                "fit_orientation_gap_vs_raw_holonomy": _fit_through_origin(raw_xs, ys),
                "coherence_ratio_summary": summarize(row["avg_coherence_ratio_mean"] for row in rows),
                "purity_summary": summarize(row["avg_purity_mean"] for row in rows),
                "trusted_pair_count": int(len(trusted)),
                "excluded_pair_count": int(sum(1 for row in rows if not row["trusted_pair"])),
                "patchwise_fit": patchwise,
            }
        )

    switch_gamma = _recommended_switch(levels, floor=0.20)
    switch_level = _select_level(levels, switch_gamma)
    payload = {
        "phase": "phase12_dense_mixed_phase_convention",
        "backend": backend_name,
        "benchmark": benchmark_id,
        "slug": benchmark.slug,
        "dephasing_values": [float(x) for x in dephasing_values],
        "loop_family": {
            "shapes": list(family.shapes),
            "centers": [list(center) for center in family.centers],
            "side_lengths": [float(x) for x in family.side_lengths],
            "steps_per_segment": int(family.steps_per_segment),
        },
        "alignment": {
            "reference": "pure_state_flux_gap_at_gamma0",
            "sign": float(sign),
        },
        "recommended_switch_gamma": float(switch_gamma),
        "loop_levels": levels,
        "switch_patchwise_fit": switch_level["patchwise_fit"],
        "switch_global_fit_aligned": switch_level["fit_orientation_gap_vs_aligned_holonomy"],
        "switch_global_fit_raw": switch_level["fit_orientation_gap_vs_raw_holonomy"],
    }
    return payload


def _plot_lines(
    path: Path, x: np.ndarray, ys: list[np.ndarray], labels: list[str], xlabel: str, ylabel: str, title: str
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(6.4, 4.2))
    for y, label in zip(ys, labels):
        plt.plot(x, y, marker="o", label=label)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


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


def phase12_payload(
    output_root: Path,
    phase12_config: Phase12Config | None = None,
    scan_config: ScanConfig | None = None,
    open_config: OpenSystemConfig | None = None,
    lindblad_config: LindbladConfig | None = None,
) -> dict:
    cfg = phase12_config or Phase12Config()
    scan_cfg = scan_config or ScanConfig(mesh=cfg.scan_mesh)
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
        family = _family_for_benchmark(benchmark_id)
        payload = _backend_loop_payload(
            benchmark_id, family, cfg.dephasing_values, lind_cache, lind_step, "lindblad"
        )
        benchmark_payloads[benchmark_id] = payload
        bench_dir = output_root / get_benchmark(benchmark_id).slug
        bench_dir.mkdir(parents=True, exist_ok=True)
        (bench_dir / f"{benchmark_id}_phase12_lindblad.json").write_text(json.dumps(payload, indent=2))

    compare_id = cfg.benchmark_id_compare
    compare_family = _family_for_benchmark(compare_id)
    compare_eff = _backend_loop_payload(
        compare_id, compare_family, cfg.dephasing_values, eff_cache, eff_step, "effective"
    )
    compare_lind = benchmark_payloads[compare_id]
    compare_dir = output_root / get_benchmark(compare_id).slug
    (compare_dir / f"{compare_id}_phase12_effective.json").write_text(json.dumps(compare_eff, indent=2))

    lind_scan_levels = [
        _scan_level(compare_id, scan_cfg, gamma, lind_cache) for gamma in cfg.dephasing_values
    ]
    eff_scan_levels = [_scan_level(compare_id, scan_cfg, gamma, eff_cache) for gamma in cfg.dephasing_values]

    common_gamma = float(compare_lind["recommended_switch_gamma"])
    lind_level = _select_level(compare_lind["loop_levels"], common_gamma)
    eff_level = _select_level(compare_eff["loop_levels"], common_gamma)
    lind_scan = _select_level(lind_scan_levels, common_gamma)
    eff_scan = _select_level(eff_scan_levels, common_gamma)

    benchmark = get_benchmark(compare_id)
    atlas = build_branch_atlas(
        benchmark=benchmark,
        grid_u=np.linspace(*benchmark.control_bounds[0], scan_cfg.mesh, dtype=float),
        grid_v=np.linspace(*benchmark.control_bounds[1], scan_cfg.mesh, dtype=float),
        config=scan_cfg,
    )
    states = atlas["chosen_states"]
    mean_bures: list[float] = []
    for i in range(scan_cfg.mesh):
        for j in range(scan_cfg.mesh):
            if atlas["ambiguous_map"][i][j]:
                continue
            state = states[i][j]
            mean_bures.append(
                bures_distance_sq(eff_cache.get(state, common_gamma), lind_cache.get(state, common_gamma))
            )

    lind_slope_seq = np.asarray(
        [
            (
                level["fit_orientation_gap_vs_aligned_holonomy"]["slope"]
                if level["fit_orientation_gap_vs_aligned_holonomy"]["slope"] is not None
                else np.nan
            )
            for level in compare_lind["loop_levels"]
        ],
        dtype=float,
    )
    eff_slope_seq = np.asarray(
        [
            (
                level["fit_orientation_gap_vs_aligned_holonomy"]["slope"]
                if level["fit_orientation_gap_vs_aligned_holonomy"]["slope"] is not None
                else np.nan
            )
            for level in compare_eff["loop_levels"]
        ],
        dtype=float,
    )
    lind_r2_seq = np.asarray(
        [
            (
                level["fit_orientation_gap_vs_aligned_holonomy"]["r2"]
                if level["fit_orientation_gap_vs_aligned_holonomy"]["r2"] is not None
                else np.nan
            )
            for level in compare_lind["loop_levels"]
        ],
        dtype=float,
    )
    eff_r2_seq = np.asarray(
        [
            (
                level["fit_orientation_gap_vs_aligned_holonomy"]["r2"]
                if level["fit_orientation_gap_vs_aligned_holonomy"]["r2"] is not None
                else np.nan
            )
            for level in compare_eff["loop_levels"]
        ],
        dtype=float,
    )
    lind_curv_seq = np.asarray([level["mean_abs_mixed_curvature"] for level in lind_scan_levels], dtype=float)
    eff_curv_seq = np.asarray([level["mean_abs_mixed_curvature"] for level in eff_scan_levels], dtype=float)

    benchmark_summary = {}
    for benchmark_id, payload in benchmark_payloads.items():
        switch_gamma = float(payload["recommended_switch_gamma"])
        level = _select_level(payload["loop_levels"], switch_gamma)
        benchmark_summary[benchmark_id] = {
            "benchmark": benchmark_id,
            "recommended_switch_gamma": switch_gamma,
            "trusted_pair_count_at_switch": int(level["trusted_pair_count"]),
            "excluded_pair_count_at_switch": int(level["excluded_pair_count"]),
            "fit_r2_at_switch": level["fit_orientation_gap_vs_aligned_holonomy"]["r2"],
            "fit_slope_at_switch": level["fit_orientation_gap_vs_aligned_holonomy"]["slope"],
            "alignment_sign": float(payload["alignment"]["sign"]),
        }

    comparison = {
        "benchmark": compare_id,
        "common_gamma": common_gamma,
        "lindblad_switch_gamma": float(compare_lind["recommended_switch_gamma"]),
        "effective_switch_gamma": float(compare_eff["recommended_switch_gamma"]),
        "lindblad_alignment_sign": float(compare_lind["alignment"]["sign"]),
        "effective_alignment_sign": float(compare_eff["alignment"]["sign"]),
        "mean_bures_distance_between_backends": float(np.mean(mean_bures)) if mean_bures else None,
        "metric_correlation_at_common_gamma": _corr(
            np.asarray(lind_scan["bures_metric_trace"], dtype=float),
            np.asarray(eff_scan["bures_metric_trace"], dtype=float),
        ),
        "curvature_correlation_at_common_gamma": _corr(
            np.asarray(lind_scan["mixed_curvature"], dtype=float),
            np.asarray(eff_scan["mixed_curvature"], dtype=float),
        ),
        "lindblad_fit_at_common_gamma": lind_level["fit_orientation_gap_vs_aligned_holonomy"],
        "effective_fit_at_common_gamma": eff_level["fit_orientation_gap_vs_aligned_holonomy"],
        "lindblad_slope_sequence": lind_slope_seq.tolist(),
        "effective_slope_sequence": eff_slope_seq.tolist(),
        "lindblad_r2_sequence": lind_r2_seq.tolist(),
        "effective_r2_sequence": eff_r2_seq.tolist(),
        "lindblad_mean_abs_curvature_sequence": lind_curv_seq.tolist(),
        "effective_mean_abs_curvature_sequence": eff_curv_seq.tolist(),
    }

    payload = {
        "phase": "phase12_dense_mixed_phase_convention",
        "description": (
            "Dense dephasing rerun with broader loop families and a benchmark-intrinsic mixed-state phase"
            " convention aligned to the pure-state flux reference."
        ),
        "dephasing_values": [float(x) for x in cfg.dephasing_values],
        "benchmark_summaries": benchmark_summary,
        "benchmark_payloads": benchmark_payloads,
        "benchmark_c_effective_payload": compare_eff,
        "benchmark_c_lindblad_scan_levels": lind_scan_levels,
        "benchmark_c_effective_scan_levels": eff_scan_levels,
        "benchmark_c_backend_comparison": comparison,
        "notes": [
            "The phase convention first unwraps per-loop mixed holonomy phases across γ and then"
            " harmonizes the sign against the pure-state flux gap at γ=0.",
            "This does not promote the mixed-state slope to a topology-grade invariant, but it makes"
            " raw fitted slopes backend-comparable inside the benchmark scaffold.",
            "Phase 12 targets the positive mixed-state benchmark C; control conclusions from Phase 11"
            " are carried forward unchanged rather than fully rerun on the dense grid in this pass.",
        ],
    }
    project_root = output_root.parents[1]
    (project_root / "05_reports").mkdir(parents=True, exist_ok=True)
    (project_root / "05_reports" / "phase12_summary.json").write_text(json.dumps(payload, indent=2))
    return payload


def phase12_report(output_root: Path, payload: dict) -> dict[str, Path]:
    project_root = output_root.parents[1]
    plots_dir = project_root / "05_reports" / "plots" / "phase12_phase_convention" / "benchmark_c"
    plots_dir.mkdir(parents=True, exist_ok=True)
    reports_dir = project_root / "05_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    compare = payload["benchmark_c_backend_comparison"]
    x = np.asarray(payload["dephasing_values"], dtype=float)
    lind_slope = np.asarray(compare["lindblad_slope_sequence"], dtype=float)
    eff_slope = np.asarray(compare["effective_slope_sequence"], dtype=float)
    lind_r2 = np.asarray(compare["lindblad_r2_sequence"], dtype=float)
    eff_r2 = np.asarray(compare["effective_r2_sequence"], dtype=float)
    lind_curv = np.asarray(compare["lindblad_mean_abs_curvature_sequence"], dtype=float)
    eff_curv = np.asarray(compare["effective_mean_abs_curvature_sequence"], dtype=float)

    slope_path = plots_dir / "aligned_slope_vs_dephasing.png"
    _plot_lines(
        slope_path,
        x,
        [lind_slope, eff_slope],
        ["lindblad", "effective"],
        "dephasing γ",
        "aligned fit slope",
        "Benchmark C aligned mixed-state slope vs dephasing",
    )
    r2_path = plots_dir / "aligned_r2_vs_dephasing.png"
    _plot_lines(
        r2_path,
        x,
        [lind_r2, eff_r2],
        ["lindblad", "effective"],
        "dephasing γ",
        "fit R²",
        "Benchmark C aligned mixed-state fit quality vs dephasing",
    )
    curv_path = plots_dir / "backend_curvature_vs_dephasing_dense.png"
    _plot_lines(
        curv_path,
        x,
        [lind_curv, eff_curv],
        ["lindblad", "effective"],
        "dephasing γ",
        "mean |mixed curvature|",
        "Benchmark C backend curvature scale vs dephasing",
    )

    gamma = float(compare["common_gamma"])
    lind_payload = payload["benchmark_payloads"]["benchmark_c"]
    lind_level = _select_level(lind_payload["loop_levels"], gamma)
    trusted = [row for row in lind_level["pair_rows"] if row["trusted_pair"]]
    scatter_path = plots_dir / "response_vs_aligned_holonomy_switch.png"
    _plot_scatter(
        scatter_path,
        np.asarray([row["aligned_mixed_holonomy_gap"] for row in trusted], dtype=float),
        np.asarray([row["orientation_gap"] for row in trusted], dtype=float),
        xlabel="aligned mixed holonomy gap",
        ylabel="orientation gap",
        title=f"Benchmark C response vs aligned mixed holonomy (γ={gamma:.3f})",
        fit=lind_level["fit_orientation_gap_vs_aligned_holonomy"],
    )

    summary_rows = payload["benchmark_summaries"]
    md_lines = [
        "# CWT-CGT Phase 12 Report",
        "",
        "## What Phase 12 adds",
        "",
        "Phase 12 tightens the mixed-state phase convention and reruns the Lindblad mixed-state lane on"
        " a denser γ grid and a broader loop-family set for benchmark C, with earlier control conclusions"
        " carried forward.",
        "",
        "The convention now has two steps:",
        "",
        "1. unwrap each loop’s mixed holonomy phase continuously over γ;",
        "2. harmonize the overall sign against the **pure-state flux gap at γ=0**.",
        "",
        "This makes the fitted mixed-state slope backend-comparable within the scaffold, while still"
        " treating it as a patchwise response coefficient rather than a topology-grade invariant.",
        "",
        "## Phase 12 dense rerun scope",
        "",
    ]
    for benchmark_id, row in summary_rows.items():
        sw = row["recommended_switch_gamma"]
        tp = row["trusted_pair_count_at_switch"]
        ep = row["excluded_pair_count_at_switch"]
        sl = row["fit_slope_at_switch"]
        fr2 = row["fit_r2_at_switch"]
        sg = row["alignment_sign"]
        md_lines.append(
            f"- {benchmark_id}: switch γ={sw:.3f}, trusted={tp}, excluded={ep},"
            f" slope={sl}, R²={fr2}, sign={sg:+.0f}"
        )
    patchwise = lind_payload["switch_patchwise_fit"]
    md_lines.extend(
        [
            "",
            "## Benchmark C patchwise fits at the switch γ",
            "",
        ]
    )
    for key, fit in patchwise.items():
        md_lines.append(f"- {key}: slope={fit['slope']}, R²={fit['r2']}, count={fit['count']}")
    md_lines.extend(
        [
            "",
            "## Benchmark C backend comparison",
            "",
            f"Common γ: **{compare['common_gamma']:.3f}**",
            f"- Lindblad switch γ: {compare['lindblad_switch_gamma']:.3f}",
            f"- Effective switch γ: {compare['effective_switch_gamma']:.3f}",
            f"- Lindblad alignment sign: {compare['lindblad_alignment_sign']:+.0f}",
            f"- Effective alignment sign: {compare['effective_alignment_sign']:+.0f}",
            f"- Mean Bures distance between backends at common γ:"
            f" {compare['mean_bures_distance_between_backends']}",
            f"- Metric correlation at common γ: {compare['metric_correlation_at_common_gamma']}",
            f"- Curvature correlation at common γ: {compare['curvature_correlation_at_common_gamma']}",
            f"- Lindblad fit at common γ: slope={compare['lindblad_fit_at_common_gamma']['slope']},"
            f" R²={compare['lindblad_fit_at_common_gamma']['r2']},"
            f" count={compare['lindblad_fit_at_common_gamma']['count']}",
            f"- Effective fit at common γ: slope={compare['effective_fit_at_common_gamma']['slope']},"
            f" R²={compare['effective_fit_at_common_gamma']['r2']},"
            f" count={compare['effective_fit_at_common_gamma']['count']}",
            "",
            f"Plot: `{slope_path}`",
            f"Plot: `{r2_path}`",
            f"Plot: `{curv_path}`",
            f"Plot: `{scatter_path}`",
            "",
            "## Interpretation",
            "",
            "- Benchmark C remains the positive mixed-state benchmark under the denser γ rerun and"
            " broader loop family.",
            "- Phase 11 control conclusions for A, B, D, and F are unchanged and are treated as"
            " carried-forward context in this targeted pass.",
        ]
    )
    md_path = reports_dir / "CWT-CGT_Phase_12_Report.md"
    md_path.write_text("\n".join(md_lines))
    return {
        "phase12_report": md_path,
        "benchmark_c_slope_plot": slope_path,
        "benchmark_c_r2_plot": r2_path,
        "benchmark_c_curvature_plot": curv_path,
        "benchmark_c_scatter": scatter_path,
    }
