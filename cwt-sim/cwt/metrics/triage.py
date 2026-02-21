"""Triage metrics for prioritising simulation runs."""

from __future__ import annotations

import math
from types import MappingProxyType
from typing import Iterable, Mapping, Sequence

import networkx as nx
import numpy as np

from ..graph.substrate import GraphSubstrate
from .refine import geom_score

__all__ = [
    "TRIAGE_WEIGHTS",
    "TRIAGE_WEIGHT_SUM",
    "triage_score",
    "placeholder_triage_score",
    "xi_static",
    "xi_dynamic",
    "xi_update_ema",
]


TRIAGE_WEIGHT_DEGREE = 0.25
TRIAGE_WEIGHT_CENTRALITY = 0.15
TRIAGE_WEIGHT_CURVATURE = 0.20
TRIAGE_WEIGHT_CLIP = 0.10
TRIAGE_WEIGHT_SUSCEPTIBILITY = 0.10
TRIAGE_WEIGHT_GEOMETRY = 0.20

TRIAGE_WEIGHTS: Mapping[str, float] = MappingProxyType(
    {
        "degree": TRIAGE_WEIGHT_DEGREE,
        "centrality": TRIAGE_WEIGHT_CENTRALITY,
        "curvature": TRIAGE_WEIGHT_CURVATURE,
        "clip": TRIAGE_WEIGHT_CLIP,
        "susceptibility": TRIAGE_WEIGHT_SUSCEPTIBILITY,
        "geometry": TRIAGE_WEIGHT_GEOMETRY,
    }
)

TRIAGE_WEIGHT_SUM = float(sum(TRIAGE_WEIGHTS.values()))
if not math.isclose(TRIAGE_WEIGHT_SUM, 1.0, rel_tol=1e-9, abs_tol=1e-9):
    raise RuntimeError(f"Triage score weights must sum to 1.0; received {TRIAGE_WEIGHT_SUM:.12f}.")


def triage_score(
    S: GraphSubstrate,
    curvature_bias: Sequence[float],
    *,
    clip_counts: Sequence[int] | None = None,
    susceptibility: np.ndarray | None = None,
    geom_stats: Mapping[str, float] | None = None,
) -> float:
    """Rank the health of a run using graph, curvature, and geometric telemetry."""

    if not isinstance(S, GraphSubstrate):
        raise TypeError("S must be a GraphSubstrate instance.")

    nodes = _ordered_nodes(S.node_index)
    if not nodes:
        raise ValueError("Graph substrate must contain at least one node.")

    degrees = _degree_vector(S.G, nodes, "out")
    degree_mean = float(np.mean(degrees))
    if degree_mean <= 0.0:
        degree_dispersion = 0.0
    else:
        degree_dispersion = float(np.std(degrees) / degree_mean)
    degree_term = 1.0 / (1.0 + degree_dispersion)

    eigen = _eigenvector_centrality(S, nodes)
    if np.allclose(eigen, 0.0):
        centrality_term = 1.0
    else:
        centrality_term = 1.0 / (1.0 + float(np.std(eigen)))

    curvature_arr = np.asarray(curvature_bias, dtype=float)
    if curvature_arr.ndim != 1 or curvature_arr.size == 0:
        raise ValueError("curvature_bias must be a non-empty one-dimensional sequence.")
    curvature_term = 1.0 / (1.0 + float(np.mean(np.abs(curvature_arr))))

    clip_term = 1.0
    if clip_counts is not None:
        clip_arr = np.asarray(list(clip_counts), dtype=float)
        if clip_arr.size:
            clip_term = 1.0 / (1.0 + float(np.mean(np.clip(clip_arr, 0.0, None))))

    susceptibility_term = 1.0
    if susceptibility is not None:
        xi = np.asarray(susceptibility, dtype=float)
        if xi.ndim != 1:
            raise ValueError("susceptibility must be one-dimensional when provided.")
        if xi.size:
            xi = np.clip(xi, 0.0, None)
            total = float(np.sum(xi))
            if total > 0.0 and np.isfinite(total):
                xi = xi / total
                entropy = -float(np.sum(xi * np.log2(np.clip(xi, 1e-12, None))))
                max_entropy = math.log2(xi.size)
                susceptibility_term = entropy / max_entropy if max_entropy > 0.0 else 1.0

    geom_term = 1.0
    if geom_stats:
        tr_g = float(geom_stats.get("tr_g", 0.0))
        det_g = float(geom_stats.get("det_g", 0.0))
        omega = float(geom_stats.get("omega", 0.0))
        alpha = float(geom_stats.get("alpha", 1.0))
        beta = float(geom_stats.get("beta", 0.2))
        gamma = float(geom_stats.get("gamma", 0.5))

        raw_geom = geom_score(tr_g, det_g, omega, alpha=alpha, beta=beta, gamma=gamma)
        raw_geom = max(raw_geom, 0.0)
        geom_term = 1.0 - float(np.exp(-raw_geom)) if raw_geom > 0.0 else 0.0
        geom_term = float(np.clip(geom_term, 0.0, 1.0))

    score = (
        TRIAGE_WEIGHTS["degree"] * degree_term
        + TRIAGE_WEIGHTS["centrality"] * centrality_term
        + TRIAGE_WEIGHTS["curvature"] * curvature_term
        + TRIAGE_WEIGHTS["clip"] * clip_term
        + TRIAGE_WEIGHTS["susceptibility"] * susceptibility_term
        + TRIAGE_WEIGHTS["geometry"] * geom_term
    )

    return float(np.clip(score, 0.0, 1.0))


def placeholder_triage_score(*args, **kwargs) -> float:
    """Compatibility shim delegating to :func:`triage_score`."""

    return triage_score(*args, **kwargs)


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

    raw = float(g1) * amp_sq + float(g2) * g_theta + float(g3) * g_p + float(g4) * s

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
