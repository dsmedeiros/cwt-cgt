"""Graph-family study linking structural statistics to curvature geometry."""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from itertools import permutations
from typing import Iterable, Mapping, Sequence

import networkx as nx
import numpy as np

from cwt.graph import factories
from cwt.graph.substrate import GraphSubstrate
from cwt.layers.state import LayersState
from cwt.orchestrator.param_path import ParameterPath
from cwt.orchestrator.scheduler import RunConfig, _psi_at, run_parameter_loop


@dataclass
class FamilyResult:
    name: str
    degree_entropy: float
    clustering: float
    modularity: float
    peak_abs_omega: float
    kappa_mean: float
    ridge_auc: float


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


def _phi_flux(record) -> float:
    total = 0.0
    for tile in record.omega_tiles:
        if not isinstance(tile, Mapping):
            continue
        try:
            omega_val = float(tile.get("omega", 0.0))
            area_val = float(tile.get("tile_area", 0.0))
        except (TypeError, ValueError):
            continue
        if math.isfinite(omega_val) and math.isfinite(area_val):
            total += omega_val * area_val
    return float(total)


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


def _eval_family(
    name: str,
    substrate: GraphSubstrate,
    *,
    center: Mapping[str, float],
    axes: tuple[str, str],
    extent: float,
    grid_size: int,
    seed: int,
) -> FamilyResult:
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

    area = float(sum(float(delta) for delta in record.delta_area))
    phi_flux = _phi_flux(record)
    kappa = phi_flux / area if area else float("nan")
    peak, auc = _ridge_auc(record)

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
        f"{'family':<6}  {'H_deg':>7}  {'C̄':>6}  {'Q':>6}  {'peak|Ω|':>9}  " f"{'κ̄₁':>9}  {'ridge AUC':>11}"
    )
    print(header)
    print("-" * len(header))
    for res in results:
        print(
            f"{res.name:<6}  {res.degree_entropy:7.3f}  {res.clustering:6.3f}  {res.modularity:6.3f}  "
            f"{res.peak_abs_omega:9.3e}  {res.kappa_mean:9.4f}  {res.ridge_auc:11.4f}"
        )

    print()
    best_modularity = max(results, key=lambda r: r.modularity)
    print("Highest modularity ensemble: " f"{best_modularity.name} (Q={best_modularity.modularity:.3f})")


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    families = [token.strip() for token in str(args.families).split(",") if token.strip()]
    axes = _parse_axes(args.axes)
    center = _parse_center(str(args.center))
    extent = float(args.extents)
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
            )
        )
    _print_results(results)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
