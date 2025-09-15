"""Graph substrate definitions for continuous wavelet transport simulations."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Tuple

import networkx as nx
import numpy as np
import scipy.sparse as sp

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GraphSubstrate:
    """Bundle network topology with canonical sparse representations."""

    G: nx.DiGraph
    node_index: dict[int, int]
    W: sp.csr_matrix
    Tau: sp.csr_matrix
    out_deg: np.ndarray
    N: int


def build_substrate(G: nx.DiGraph) -> GraphSubstrate:
    """Construct a :class:`GraphSubstrate` from a directed graph.

    Parameters
    ----------
    G:
        Directed graph whose edges carry ``weight`` and ``delay`` attributes.

    Returns
    -------
    GraphSubstrate
        Immutable bundle containing the original graph and its sparse matrices.
    """

    if not isinstance(G, nx.DiGraph):
        G = nx.DiGraph(G)
    else:
        G = G.copy()

    node_index = to_sorted_index(G)
    require_nonnegative_weights(G)
    require_positive_delays(G)
    W, Tau, out_deg = graph_arrays(G, node_index)

    return GraphSubstrate(G=G, node_index=node_index, W=W, Tau=Tau, out_deg=out_deg, N=len(node_index))


def require_nonnegative_weights(G: nx.DiGraph) -> None:
    """Ensure every edge carries a non-negative weight."""

    for u, v, data in G.edges(data=True):
        weight = data.get("weight", 1.0)
        if weight is None:
            weight = 0.0
        if weight < 0:
            raise ValueError(f"Edge {u!r}->{v!r} has negative weight {weight}.")
        data["weight"] = float(weight)


def require_positive_delays(G: nx.DiGraph) -> None:
    """Ensure every edge carries a strictly positive delay."""

    for u, v, data in G.edges(data=True):
        delay = data.get("delay", 1.0)
        if delay is None:
            delay = 1.0
        if delay <= 0:
            raise ValueError(f"Edge {u!r}->{v!r} has non-positive delay {delay}.")
        data["delay"] = float(delay)


def to_sorted_index(G: nx.DiGraph) -> dict[int, int]:
    """Map node labels to contiguous indices in ascending order."""

    nodes = list(G.nodes)
    if not nodes:
        return {}

    try:
        sorted_nodes = sorted(nodes)
    except TypeError:
        sorted_nodes = sorted(nodes, key=lambda label: str(label))
        logger.warning(
            "Graph nodes are not mutually orderable; canonical index is derived from string ordering."
        )

    if any(not isinstance(label, int) or label != idx for idx, label in enumerate(sorted_nodes)):
        logger.warning(
            "Graph nodes are not labelled consecutively from 0..N-1; using canonical index mapping to contiguous integers."
        )

    return {label: idx for idx, label in enumerate(sorted_nodes)}


def graph_arrays(G: nx.DiGraph, node_index: dict[int, int]) -> Tuple[sp.csr_matrix, sp.csr_matrix, np.ndarray]:
    """Create sparse weight and delay matrices aligned with ``node_index``."""

    N = len(node_index)
    if N == 0:
        empty = sp.csr_matrix((0, 0), dtype=float)
        return empty, empty.copy(), np.zeros((0,), dtype=np.int64)

    rows: list[int] = []
    cols: list[int] = []
    weight_data: list[float] = []
    delay_data: list[float] = []
    out_deg = np.zeros((N,), dtype=np.int64)

    for u, v, data in G.edges(data=True):
        try:
            col = node_index[u]
            row = node_index[v]
        except KeyError as exc:  # pragma: no cover - defensive programming
            raise KeyError(f"Node {exc.args[0]!r} missing from node_index mapping.") from exc

        weight = float(data.get("weight", 1.0))
        delay = float(data.get("delay", 1.0))

        rows.append(row)
        cols.append(col)
        weight_data.append(weight)
        delay_data.append(delay)

        if weight > 0:
            out_deg[col] += 1

    shape = (N, N)
    W = sp.csr_matrix((weight_data, (rows, cols)), shape=shape, dtype=float)
    Tau = sp.csr_matrix((delay_data, (rows, cols)), shape=shape, dtype=float)

    return W, Tau, out_deg
