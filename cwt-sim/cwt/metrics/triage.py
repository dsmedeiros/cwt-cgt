"""Triage metrics scaffolding."""

from __future__ import annotations

from typing import Iterable

import networkx as nx
import numpy as np

from ..graph.substrate import GraphSubstrate

__all__ = [
    "placeholder_triage_score",
    "xi_static",
    "xi_dynamic",
    "xi_update_ema",
]


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


def xi_dynamic(
    S: GraphSubstrate,
    Psi: np.ndarray,
    pQ: np.ndarray,
    theta: np.ndarray,
    g1: float,
    g2: float,
    g3: float,
    g4: float,
) -> np.ndarray:
    r"""Return the dynamic susceptibility :math:`\Xi_n^{(dyn)}`.

    The score combines multiple observables, each normalised to the unit
    interval before aggregation and final renormalisation to form a
    probability distribution.
    """

    if not isinstance(S, GraphSubstrate):
        raise TypeError("S must be a GraphSubstrate instance.")

    N = S.N
    if N == 0:
        return np.zeros((0,), dtype=float)

    Psi_arr = np.asarray(Psi, dtype=complex)
    pQ_arr = np.asarray(pQ, dtype=float)
    theta_arr = np.asarray(theta, dtype=float)

    if Psi_arr.ndim != 1 or Psi_arr.size != N:
        raise ValueError("Psi must be a one-dimensional array aligned with the substrate.")
    if pQ_arr.ndim != 1 or pQ_arr.size != N:
        raise ValueError("pQ must be a one-dimensional array aligned with the substrate.")
    if theta_arr.ndim != 1 or theta_arr.size != N:
        raise ValueError("theta must be a one-dimensional array aligned with the substrate.")

    amp_sq = np.abs(Psi_arr) ** 2

    W = S.W.tocoo()
    g_theta_raw = np.zeros(N, dtype=float)
    g_p_raw = np.zeros(N, dtype=float)

    if W.nnz > 0:
        theta_diff = np.sin(theta_arr[W.col] - theta_arr[W.row])
        np.add.at(g_theta_raw, W.row, W.data * theta_diff)

        sqrt_p = np.sqrt(np.clip(pQ_arr, 0.0, None))
        delta = sqrt_p[W.col] - sqrt_p[W.row]
        positive = np.maximum(delta, 0.0)
        np.add.at(g_p_raw, W.row, W.data * positive)

    g_theta = np.abs(g_theta_raw)
    theta_norm = float(np.max(g_theta))
    if theta_norm > 0.0 and np.isfinite(theta_norm):
        g_theta /= theta_norm
    else:
        g_theta.fill(0.0)

    gp_norm = float(np.max(g_p_raw))
    if gp_norm > 0.0 and np.isfinite(gp_norm):
        g_p = g_p_raw / gp_norm
    else:
        g_p = np.zeros_like(g_p_raw)

    W_csr = S.W.tocsr()
    s = np.zeros(N, dtype=float)
    for idx in range(N):
        start = W_csr.indptr[idx]
        end = W_csr.indptr[idx + 1]
        if end <= start:
            continue
        neighbours = W_csr.indices[start:end]
        local = np.exp(1j * theta_arr[neighbours])
        s[idx] = float(np.abs(np.mean(local)))

    raw = (
        float(g1) * amp_sq
        + float(g2) * g_theta
        + float(g3) * g_p
        + float(g4) * s
    )

    raw = np.clip(raw, 0.0, None)

    total = float(np.sum(raw))
    if not np.isfinite(total) or total <= 0.0:
        return np.full((N,), 1.0 / float(N), dtype=float)

    return raw / total


def xi_update_ema(prev_xi: np.ndarray, new_xi: np.ndarray, kappa: float) -> np.ndarray:
    r"""Low-pass filter for susceptibility updates.

    The function computes the exponential moving average
    ``(1 - kappa) * prev_xi + kappa * new_xi`` and renormalises the result
    to form a probability vector.  A small :math:`\kappa` produces a
    contractive update towards the steady state.
    """

    prev = np.asarray(prev_xi, dtype=float)
    new = np.asarray(new_xi, dtype=float)

    if prev.shape != new.shape:
        raise ValueError("prev_xi and new_xi must have the same shape.")
    if prev.ndim != 1:
        raise ValueError("Susceptibility vectors must be one-dimensional.")

    if prev.size == 0:
        return np.zeros((0,), dtype=float)

    kappa = float(kappa)

    mixed = (1.0 - kappa) * prev + kappa * new
    mixed = np.clip(mixed, 0.0, None)

    total = float(np.sum(mixed))
    if not np.isfinite(total) or total <= 0.0:
        return np.full(prev.shape, 1.0 / float(prev.size), dtype=float)

    return mixed / total
