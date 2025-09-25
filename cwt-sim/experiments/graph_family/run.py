"""Graph-family study linking structural statistics to curvature geometry."""

from __future__ import annotations

import argparse
import json
import math
import time
from dataclasses import asdict, dataclass
from itertools import permutations
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import networkx as nx
import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from cwt.graph import factories
from cwt.graph.substrate import GraphSubstrate
from cwt.layers.state import LayersState
from cwt.orchestrator.param_path import ParameterPath
from cwt.orchestrator.scheduler import RunConfig, RunRecord, _psi_at, run_parameter_loop


@dataclass
class FamilyResult:
    name: str
    degree_entropy: float
    clustering: float
    modularity: float
    peak_abs_omega: float
    kappa_mean: float
    ridge_auc: float
    phi_missing: bool
    median_abs_omega: float = float("nan")
    phi_flux: float | None = None
    phi_flux_missing: bool = False
    fs_p95: float = float("nan")
    fs_boundary: float = float("nan")
    fs_exceeded: bool = False
    fs_guard_enabled: bool = False
    runtime_seconds: float | None = None
    thumbnail: str | None = None


def _loop_steps(extent: float, grid_size: int) -> int:
    magnitude = abs(float(extent))
    if magnitude <= 0.0:
        raise ValueError("extent must be positive")
    base = max(int(grid_size), 4)
    scale = max(int(round(magnitude / 0.01)), 1)
    return base * scale


def _run_config() -> RunConfig:
    return RunConfig(
        eta_q=0.32,
        zeta=0.0,
        omega_scale=1.0,
        s_min=0.6,
        smooth_window=3,
        compute_metric=False,
        compute_curvature=True,
        adapt_levels=1,
        ci_tol=0.05,
        alpha=0.35,
        beta=1.0,
        neighbor_settle_steps=40,
        geometry={"sample_mode": "direct", "neighbor_steps": 1},
        delta_frac={"tau": 0.01, "zeta": 0.01},
        xi_kind={"type": "static"},
        readout={"final": True},
        noise={},
        fs_step_guard={},
    )


def _phi_flux(record) -> tuple[float, bool]:
    total = 0.0
    tiles_present = False
    for tile in record.omega_tiles:
        if not isinstance(tile, Mapping):
            continue
        try:
            omega_val = float(tile.get("omega", 0.0))
            area_val = float(tile.get("tile_area", 0.0))
        except (TypeError, ValueError):
            continue
        if math.isfinite(omega_val) and math.isfinite(area_val):
            tiles_present = True
            total += omega_val * area_val
    if not tiles_present:
        return 0.0, True
    return float(total), False


def _ridge_auc(record) -> tuple[float, float]:
    peak = 0.0
    total_area = 0.0
    accum = 0.0
    for tile in record.omega_tiles:
        if not isinstance(tile, Mapping):
            continue
        try:
            omega_val = abs(float(tile.get("omega", 0.0)))
            area_val = abs(float(tile.get("tile_area", 0.0)))
        except (TypeError, ValueError):
            continue
        if not (math.isfinite(omega_val) and math.isfinite(area_val)):
            continue
        peak = max(peak, omega_val)
        total_area += area_val
        accum += omega_val * area_val
    auc = accum / total_area if total_area else float("nan")
    return peak, auc


def _entropy(values: Iterable[int]) -> float:
    arr = np.asarray(list(values), dtype=float)
    if arr.size == 0:
        return float("nan")
    counts = np.bincount(arr.astype(int))
    probs = counts / counts.sum() if counts.sum() else np.zeros_like(counts, dtype=float)
    mask = probs > 0
    if not mask.any():
        return 0.0
    entropy = -np.sum(probs[mask] * np.log(probs[mask]))
    return float(entropy)


def _modularity(G: nx.Graph) -> float:
    if G.number_of_edges() == 0:
        return 0.0
    communities = nx.algorithms.community.greedy_modularity_communities(G)
    return float(nx.algorithms.community.modularity(G, communities))


def _initial_state(
    substrate: GraphSubstrate, center: Mapping[str, float], config: RunConfig
) -> tuple[np.ndarray, np.ndarray]:
    N = substrate.N
    base_prob = np.full(N, 1.0 / N, dtype=float)
    base_theta = np.zeros(N, dtype=float)
    settle_steps = max(int(getattr(config, "neighbor_settle_steps", 40)), 1)
    psi_center = _psi_at(substrate, center, base_prob, base_theta, config, steps=settle_steps)
    return np.square(np.abs(psi_center)).astype(float), np.angle(psi_center).astype(float)


def _median_abs_omega(record: RunRecord) -> float:
    values: list[float] = []
    for tile in record.omega_tiles:
        if not isinstance(tile, Mapping):
            continue
        try:
            omega_val = float(tile.get("omega", 0.0))
        except (TypeError, ValueError):
            continue
        if math.isfinite(omega_val):
            values.append(abs(omega_val))
    if not values:
        return float("nan")
    return float(np.median(np.asarray(values, dtype=float)))


def _fs_guard_meta(record: RunRecord) -> tuple[float, float, bool, bool]:
    meta = record.meta.get("fs_step_guard", {}) if isinstance(record.meta, Mapping) else {}
    try:
        fs_p95 = float(meta.get("p95", float("nan")))
    except (TypeError, ValueError):
        fs_p95 = float("nan")
    try:
        fs_boundary = float(meta.get("boundary", float("nan")))
    except (TypeError, ValueError):
        fs_boundary = float("nan")
    fs_exceeded = bool(meta.get("boundary_exceeded", False))
    fs_enabled = bool(meta.get("enabled", False))
    return fs_p95, fs_boundary, fs_exceeded, fs_enabled


def _render_fs_thumbnail(name: str, record: RunRecord, out_dir: Path) -> str | None:
    if not record.fs_steps:
        return None

    steps = np.arange(1, len(record.fs_steps) + 1, dtype=float)
    values = np.asarray(record.fs_steps, dtype=float)
    if steps.size == 0:
        return None

    fig = Figure(figsize=(2.6, 1.8), dpi=150)
    canvas = FigureCanvasAgg(fig)
    ax = fig.add_subplot(1, 1, 1)

    ax.plot(steps, values, color="#2563eb", linewidth=1.2, label="FS step")

    fs_p95, fs_boundary, _, fs_enabled = _fs_guard_meta(record)
    if fs_enabled and math.isfinite(fs_boundary):
        ax.axhline(fs_boundary, color="#dc2626", linestyle="--", linewidth=0.9, label="guard")

    ax.set_title(f"{name} FS trajectory", fontsize=8)
    ax.set_xlabel("step", fontsize=7)
    ax.set_ylabel("FS distance", fontsize=7)
    ax.tick_params(axis="both", labelsize=6)
    ax.set_xlim(1, max(float(steps[-1]), 1.0))
    finite_vals = values[np.isfinite(values)]
    if finite_vals.size:
        ymax = float(finite_vals.max()) * 1.1 if finite_vals.max() > 0 else 0.1
        ax.set_ylim(bottom=0.0, top=max(ymax, fs_boundary * 1.2 if math.isfinite(fs_boundary) else 0.1))
    ax.legend(fontsize=6, loc="upper right")
    fig.tight_layout(pad=0.4)

    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{name.lower()}_fs.png"
    canvas.print_png(out_dir / filename)
    fig.clf()
    return filename


def _eval_family(
    name: str,
    substrate: GraphSubstrate,
    *,
    center: Mapping[str, float],
    axes: tuple[str, str],
    extent: float,
    grid_size: int,
    seed: int,
    output_dir: Path | None = None,
) -> FamilyResult:
    start = time.perf_counter()
    config = _run_config()
    base_prob, base_theta = _initial_state(substrate, center, config)

    steps = _loop_steps(extent, grid_size)
    center_dict = {axis: float(center.get(axis, 0.0)) for axis in axes}
    extent_dict = {axis: float(extent) for axis in axes}
    path = ParameterPath(
        kind="rectangle",
        center=center_dict,
        extents=extent_dict,
        steps=steps,
        orientation="CCW",
        axes=axes,
    )

    record = run_parameter_loop(
        substrate,
        LayersState(pQ=base_prob.copy(), theta=base_theta.copy()),
        path,
        config,
        seed=seed,
    )

    runtime = time.perf_counter() - start

    area = float(sum(float(delta) for delta in record.delta_area))
    phi_flux, phi_missing = _phi_flux(record)
    if phi_missing:
        kappa = float("nan")
    else:
        kappa = phi_flux / area if area else float("nan")
    peak, auc = _ridge_auc(record)
    median_abs_omega = _median_abs_omega(record)
    fs_p95, fs_boundary, fs_exceeded, fs_enabled = _fs_guard_meta(record)

    thumbnail = None
    if output_dir is not None:
        thumbnail = _render_fs_thumbnail(name, record, output_dir)

    G = substrate.G
    undirected = G.to_undirected()
    entropy = _entropy(G.out_degree(n) for n in G.nodes())
    clustering = (
        float(np.mean(list(nx.clustering(undirected).values())))
        if undirected.number_of_nodes()
        else float("nan")
    )
    modularity = _modularity(undirected)

    return FamilyResult(
        name=name,
        degree_entropy=entropy,
        clustering=clustering,
        modularity=modularity,
        peak_abs_omega=peak,
        kappa_mean=kappa,
        ridge_auc=auc,
        phi_missing=phi_missing,
        median_abs_omega=median_abs_omega,
        phi_flux=None if phi_missing else float(phi_flux),
        phi_flux_missing=phi_missing,
        fs_p95=fs_p95,
        fs_boundary=fs_boundary,
        fs_exceeded=fs_exceeded,
        fs_guard_enabled=fs_enabled,
        runtime_seconds=runtime,
        thumbnail=thumbnail,
    )


def _directed_from_undirected(G: nx.Graph, weight: float = 1.0, delay: float = 1.0) -> nx.DiGraph:
    H = nx.DiGraph()
    for node in G.nodes():
        H.add_node(node)
    for u, v in G.edges():
        H.add_edge(u, v, weight=weight, delay=delay)
        H.add_edge(v, u, weight=weight, delay=delay)
    return H


def _modular_graph(n: int, intra_p: float, inter_p: float, seed: int) -> nx.DiGraph:
    rng = np.random.default_rng(seed)
    nodes = list(range(n))
    half = n // 2
    community_a = nodes[:half]
    community_b = nodes[half:]
    G = nx.DiGraph()
    for node in nodes:
        G.add_node(node)
    for source, target in permutations(community_a, 2):
        if rng.random() < intra_p:
            G.add_edge(source, target, weight=1.0, delay=1.0)
    for source, target in permutations(community_b, 2):
        if rng.random() < intra_p:
            G.add_edge(source, target, weight=1.0, delay=1.0)
    for source in community_a:
        for target in community_b:
            if rng.random() < inter_p:
                G.add_edge(source, target, weight=1.0, delay=1.0)
            if rng.random() < inter_p:
                G.add_edge(target, source, weight=1.0, delay=1.0)
    return G


def _build_family(name: str, seed: int) -> GraphSubstrate:
    key = name.lower()
    if key == "ring":
        G = nx.DiGraph()
        N = 12
        for node in range(N):
            nxt = (node + 1) % N
            G.add_edge(node, nxt, weight=1.0, delay=1.0 + 0.1 * (node % 3))
        return factories.build_substrate(G)
    if key == "rr":
        return factories.random_regular_digraph(14, 3, weight=1.0, delay=1.0, seed=seed)
    if key == "sw":
        undirected = nx.watts_strogatz_graph(14, 4, 0.2, seed=seed)
        return factories.build_substrate(_directed_from_undirected(undirected))
    if key == "sf":
        base = nx.scale_free_graph(14, seed=seed)
        G = nx.DiGraph()
        for node in base.nodes():
            G.add_node(int(node))
        for u, v in base.edges():
            if int(u) == int(v):
                continue
            G.add_edge(int(u), int(v), weight=1.0, delay=1.0)
        return factories.build_substrate(G)
    if key == "mod":
        G = _modular_graph(16, intra_p=0.7, inter_p=0.15, seed=seed)
        return factories.build_substrate(G)
    raise ValueError(f"unknown family '{name}'")


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Graph-family curvature survey")
    parser.add_argument("--families", type=str, default="ring,rr,sw,sf,mod")
    parser.add_argument("--axes", nargs=2, default=["tau", "zeta"])
    parser.add_argument("--grid-size", type=int, default=21)
    parser.add_argument("--extents", type=float, default=0.02)
    parser.add_argument("--center", type=str, default="tau=0.8,zeta=0.0")
    parser.add_argument("--seed", type=int, default=123)
    parser.add_argument("--out-dir", type=str, default="")
    return parser.parse_args(argv)


def _parse_center(text: str) -> dict[str, float]:
    center: dict[str, float] = {"tau": 0.0, "zeta": 0.0}
    parts = [item.strip() for item in text.split(",") if item.strip()]
    for part in parts:
        if "=" not in part:
            raise ValueError(f"malformed centre entry '{part}'")
        key, value = (token.strip() for token in part.split("=", 1))
        center[key] = float(value)
    return center


def _parse_axes(values: Sequence[str]) -> tuple[str, str]:
    if len(values) != 2:
        raise ValueError("two axes required")
    ax_i, ax_j = (str(axis).strip() for axis in values)
    if ax_i == ax_j:
        raise ValueError("axes must be distinct")
    return ax_i, ax_j


def _print_results(results: Sequence[FamilyResult]) -> None:
    header = (
        f"{'family':<6}  {'H_deg':>7}  {'C̄':>6}  {'Q':>6}  {'median|Ω|':>11}  "
        f"{'Φ_guard':>9}  {'FS p95':>8}  {'κ̄₁':>9}  {'ridge AUC':>11}"
    )
    print(header)
    print("-" * len(header))
    for res in results:
        phi_guard = res.phi_flux if res.fs_guard_enabled and not res.fs_exceeded else float("nan")
        print(
            f"{res.name:<6}  {res.degree_entropy:7.3f}  {res.clustering:6.3f}  {res.modularity:6.3f}  "
            f"{res.median_abs_omega:11.3e}  {phi_guard:9.3f}  {res.fs_p95:8.3f}  "
            f"{res.kappa_mean:9.4f}  {res.ridge_auc:11.4f}"
        )

    flagged = [res.name for res in results if res.phi_missing]
    if flagged:
        print()
        print("⚠️  Missing curvature tiles for families: " + ", ".join(flagged))

    print()
    best_modularity = max(results, key=lambda r: r.modularity)
    print("Highest modularity ensemble: " f"{best_modularity.name} (Q={best_modularity.modularity:.3f})")


def _sanitize_float(value: float | None) -> float | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(numeric) or not math.isfinite(numeric):
        return None
    return numeric


def _write_summary(
    results: Sequence[FamilyResult],
    axes: tuple[str, str],
    extent: float,
    grid_size: int,
    seed: int,
    out_dir: Path,
) -> Path:
    payload: dict[str, object] = {
        "axes": list(axes),
        "extent": float(extent),
        "grid_size": int(grid_size),
        "seed": int(seed),
        "created_at": time.time(),
        "runtime_seconds": _sanitize_float(
            sum(res.runtime_seconds or 0.0 for res in results) if results else 0.0
        ),
        "families": [],
    }

    family_entries: list[dict[str, object]] = []
    for res in results:
        entry = asdict(res)
        entry["degree_entropy"] = _sanitize_float(res.degree_entropy)
        entry["clustering"] = _sanitize_float(res.clustering)
        entry["modularity"] = _sanitize_float(res.modularity)
        entry["peak_abs_omega"] = _sanitize_float(res.peak_abs_omega)
        entry["kappa_mean"] = _sanitize_float(res.kappa_mean)
        entry["ridge_auc"] = _sanitize_float(res.ridge_auc)
        entry["median_abs_omega"] = _sanitize_float(res.median_abs_omega)
        entry["phi_flux"] = _sanitize_float(res.phi_flux)
        entry["fs_p95"] = _sanitize_float(res.fs_p95)
        entry["fs_boundary"] = _sanitize_float(res.fs_boundary)
        entry["runtime_seconds"] = _sanitize_float(res.runtime_seconds)
        thumbnail = res.thumbnail
        entry["thumbnail"] = str(thumbnail) if thumbnail else None
        family_entries.append(entry)

    payload["families"] = family_entries

    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return summary_path


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    families = [token.strip() for token in str(args.families).split(",") if token.strip()]
    axes = _parse_axes(args.axes)
    center = _parse_center(str(args.center))
    extent = float(args.extents)
    out_dir = Path(str(args.out_dir)).expanduser().resolve() if str(args.out_dir).strip() else None
    results: list[FamilyResult] = []
    for index, name in enumerate(families):
        substrate = _build_family(name, seed=int(args.seed) + index)
        results.append(
            _eval_family(
                name,
                substrate,
                center=center,
                axes=axes,
                extent=extent,
                grid_size=int(args.grid_size),
                seed=int(args.seed) + 10 * index,
                output_dir=out_dir,
            )
        )
    _print_results(results)
    if out_dir is not None:
        _write_summary(results, axes, extent, int(args.grid_size), int(args.seed), out_dir)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
