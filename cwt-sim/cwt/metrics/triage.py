"""Triage metrics scaffolding."""

from __future__ import annotations

from typing import Iterable

import networkx as nx
import numpy as np

from ..graph.substrate import GraphSubstrate

__all__ = ["placeholder_triage_score", "xi_static"]


def placeholder_triage_score() -> float:
    """Return a neutral triage score."""

    return 0.0


def _pow_with_zeros(values: np.ndarray, exponent: float) -> np.ndarray:
    """Raise ``values`` to ``exponent`` while keeping zeros finite."""

    values = np.asarray(values, dtype=float)
    exponent = float(exponent)

    if values.size == 0:
        return values.copy()
    if exponent == 0.0:
        return np.ones_like(values, dtype=float)

    values = np.clip(values, 0.0, None)
    result = np.zeros_like(values, dtype=float)
    mask = values > 0.0
    if not np.any(mask):
        return result

    result[mask] = np.power(values[mask], exponent)
    return result


def _ordered_nodes(index: dict[int, int]) -> list[int]:
    """Return node labels sorted by their canonical index."""

    return [node for node, _ in sorted(index.items(), key=lambda item: item[1])]


def _degree_vector(G: nx.DiGraph, nodes: Iterable[int], which: str) -> np.ndarray:
    """Return degrees aligned with ``nodes`` for the requested direction."""

    mode = str(which).lower()
    if mode in {"out", "outdegree", "out-degree"}:
        deg_view = G.out_degree(weight="weight")
    elif mode in {"in", "indegree", "in-degree"}:
        deg_view = G.in_degree(weight="weight")
    elif mode in {"total", "all", "both", "degree", "sum", "undirected", "inout", "outin"}:
        deg_view = G.degree(weight="weight")
    else:  # pragma: no cover - defensive check
        raise ValueError(f"Unsupported degree selector {which!r}.")

    return np.asarray([float(deg_view[node]) for node in nodes], dtype=float)


def _eigenvector_centrality(S: GraphSubstrate, nodes: Iterable[int]) -> np.ndarray:
    """Return eigenvector centrality aligned with ``nodes``."""

    G_u = S.G.to_undirected(as_view=False)
    centrality = np.zeros((S.N,), dtype=float)

    if G_u.number_of_nodes() == 0:
        return centrality

    for component in nx.connected_components(G_u):
        subgraph = G_u.subgraph(component)
        if subgraph.number_of_nodes() == 0:
            continue
        if subgraph.number_of_edges() == 0:
            for node in subgraph.nodes:
                centrality[S.node_index[node]] = 1.0
            continue
        scores = nx.eigenvector_centrality_numpy(subgraph, weight="weight")
        for node, value in scores.items():
            centrality[S.node_index[node]] = float(value)

    ordered_indices = [S.node_index[node] for node in nodes]
    return centrality[ordered_indices]


def xi_static(
    S: GraphSubstrate,
    degree_pow: float = 1.0,
    eig_pow: float = 1.0,
    which: str = "out",
) -> np.ndarray:
    """Return the static susceptibility combining degree and eigenvector centrality."""

    if not isinstance(S, GraphSubstrate):
        raise TypeError("S must be a GraphSubstrate instance.")

    N = S.N
    if N == 0:
        return np.zeros((0,), dtype=float)

    nodes = _ordered_nodes(S.node_index)
    degrees = _degree_vector(S.G, nodes, which)
    eig_cent = _eigenvector_centrality(S, nodes)

    degree_factor = _pow_with_zeros(degrees, degree_pow)
    eig_factor = _pow_with_zeros(eig_cent, eig_pow)
    raw = degree_factor * eig_factor

    total = float(np.sum(raw))
    if not np.isfinite(total) or total <= 0.0:
        return np.full((N,), 1.0 / float(N), dtype=float)

    return raw / total
