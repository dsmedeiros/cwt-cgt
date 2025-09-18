"""Utilities for creating small canonical graph substrates."""

from __future__ import annotations

from typing import Iterable, Tuple

import networkx as nx

from .substrate import GraphSubstrate, build_substrate


def _prepare_graph(edges: Iterable[Tuple[int, int]], weight: float, delay: float) -> nx.DiGraph:
    G = nx.DiGraph()
    for source, target in edges:
        G.add_edge(source, target, weight=float(weight), delay=float(delay))
    return G


def dimer(weight: float = 1.0, delay: float = 1.0, bidir: bool = True) -> GraphSubstrate:
    """Two-node graph with an edge in each direction by default."""

    edges = [(0, 1)]
    if bidir:
        edges.append((1, 0))
    return build_substrate(_prepare_graph(edges, weight, delay))


def line3(weight: float = 1.0, delay: float = 1.0, bidir: bool = False) -> GraphSubstrate:
    """Chain of three nodes (0-1-2)."""

    edges = [(0, 1), (1, 2)]
    if bidir:
        edges.extend([(1, 0), (2, 1)])
    return build_substrate(_prepare_graph(edges, weight, delay))


def ring3(
    weight: float = 1.0,
    delay: float = 1.0,
    delays: Iterable[float] | None = None,
) -> GraphSubstrate:
    """Three-node directed ring 0→1→2→0.

    When ``delays`` is not provided, the ring uses a geometric progression of
    delays ``[delay, 1.5 * delay, 2.25 * delay]`` that preserves the legacy
    heterogeneity built into earlier placeholder experiments.
    """

    edges = [(0, 1), (1, 2), (2, 0)]
    if delays is None:
        base = float(delay)
        delay_values = [base, 1.5 * base, 2.25 * base]
    else:
        delay_values = [float(value) for value in delays]
    if len(delay_values) != len(edges):
        raise ValueError("delays must provide exactly three values for ring3.")

    G = nx.DiGraph()
    for (source, target), edge_delay in zip(edges, delay_values):
        G.add_edge(source, target, weight=float(weight), delay=float(edge_delay))
    return build_substrate(G)


def ring3_hetero(
    weight: float = 1.0,
    delays: Iterable[float] | None = None,
) -> GraphSubstrate:
    """Three-node ring with heterogeneous delays tuned for curvature probes."""

    if delays is None:
        delays = (1.0, 1.5, 2.2)
    return ring3(weight=weight, delays=delays)


def random_regular_digraph(
    N: int,
    out_degree: int,
    weight: float = 1.0,
    delay: float = 1.0,
    seed: int = 1,
    alpha: float = 1.0,
) -> GraphSubstrate:
    """Generate a random k-out regular directed graph and build its substrate.

    The ``alpha`` parameter controls the probability of selecting a new target
    during the construction and defaults to ``1.0`` which matches the behaviour
    of older NetworkX releases.
    """

    if N < 0:
        raise ValueError("N must be non-negative")
    if out_degree < 0:
        raise ValueError("out_degree must be non-negative")
    if N == 0:
        if out_degree != 0:
            raise ValueError("out_degree must be zero when no nodes are present")
        return build_substrate(nx.DiGraph())
    if out_degree >= N:
        raise ValueError("out_degree must be less than number of nodes for simple digraph")

    rng = nx.utils.create_random_state(seed)
    G = nx.random_k_out_graph(N, out_degree, alpha, self_loops=False, seed=rng)
    G = nx.DiGraph(G)
    for source, target in G.edges():
        G[source][target]["weight"] = float(weight)
        G[source][target]["delay"] = float(delay)
    return build_substrate(G)


def from_edgelist(edges: Iterable[Tuple[int, int, float, float]]) -> GraphSubstrate:
    """Create a substrate from an edge list (source, target, weight, delay)."""

    G = nx.DiGraph()
    for source, target, weight, delay in edges:
        G.add_edge(source, target, weight=float(weight), delay=float(delay))
    return build_substrate(G)
