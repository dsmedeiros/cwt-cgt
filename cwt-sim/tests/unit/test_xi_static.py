"""Tests for the static susceptibility metric."""

from __future__ import annotations

import numpy as np
import pytest

import networkx as nx

from cwt.graph.substrate import build_substrate
from cwt.metrics.triage import xi_static


def test_xi_static_star_graph_center_dominates() -> None:
    G = nx.DiGraph()
    center = 0
    leaves = range(1, 6)
    for leaf in leaves:
        G.add_edge(center, leaf, weight=1.0, delay=1.0)
        G.add_edge(leaf, center, weight=1.0, delay=1.0)

    S = build_substrate(G)
    Xi = xi_static(S)

    assert Xi.shape == (S.N,)
    assert np.isclose(Xi.sum(), 1.0)
    assert np.all(Xi >= 0.0)

    center_idx = S.node_index[center]
    leaf_idx = S.node_index[next(iter(leaves))]
    assert Xi[center_idx] > Xi[leaf_idx]


def test_xi_static_uniform_on_edgeless() -> None:
    G = nx.DiGraph()
    G.add_nodes_from(range(4))

    S = build_substrate(G)
    Xi = xi_static(S)

    expected = np.full(S.N, 1.0 / float(S.N))
    np.testing.assert_allclose(Xi, expected)


def test_xi_static_invalid_degree_selector() -> None:
    G = nx.DiGraph()
    G.add_edge(0, 1, weight=1.0, delay=1.0)

    S = build_substrate(G)

    with pytest.raises(ValueError):
        xi_static(S, which="invalid")
